#!/bin/sh

cd $(dirname "$0")

setup_colors() {
    local color_file="colors.sh"

    if [ ! -f "${color_file}" ]; then
        echo "${color_file} not found."
        exit 1
    fi

    . ./${color_file}
}

sudo_check() {
    local cur_file=$(basename "$0")

    if [ $(id -u) -ne 0 ]; then
        echo_error "script ${cur_file} needs to be run with superuser privileges"
        exit 1
    fi

    echo_info "running as sudo user"
}

enable_event() {
    local event_name=$1
    local event_enable_path=${event_name}/"enable" 

    if [ ! -f ${event_enable_path} ]; then
        echo_warning "event ${event_name} doesn't exist"
    else
        echo 1 > ${event_enable_path}

        # Sometimes weirdness happens...
        while [ "$(cat "${event_enable_path}")" != "1" ]; do
            echo_warning "problems with event ${event_name} enabling; retrying"
            enable_event $1
        done

        echo_info "successfully enabled ${event_name}"
    fi
}

setup_buffers() {
    local tracing_dir=$1

    # emptying previous trace
    echo "" > "${tracing_dir}/trace"

    # assumption of 2Mb is enough
    echo 2048 > "${tracing_dir}/buffer_size_kb"
}

enable_required_events() {
    local events_path="$1/events"

    # disable all active events
    echo 0 > "${events_path}/enable" 

    local events="\
        sched/sched_wakeup sched/sched_switch sched/sched_waking \
        irq/irq_handler_entry irq/irq_handler_exit \
        irq/softirq_entry irq/softirq_exit \
        irq/tasklet_entry irq/tasklet_exit \
    "
    for ev in ${events}; do
        enable_event ${events_path}/${ev}
    done
}

enable_required() {
    local tracing_dir=$1
    setup_buffers ${tracing_dir}
    enable_required_events ${tracing_dir}
    echo_info "requirements enabling finished"
}

collect_trace() {
    tracing_dir=$1
    seconds=$2
    output_file=$3

    trace_enable_path="${tracing_dir}/tracing_on"
    trace_pipe_path="${tracing_dir}/trace_pipe"

    echo 1 > ${trace_enable_path}
    timeout ${seconds} cat ${trace_pipe_path} > ${output_file}
    echo 0 > ${trace_enable_path}

    output_sz=$(du -hs ${output_file} | cut -f 1)
    output_filepath=$(readlink -f ${output_file})
    echo_info "output filesize=${output_sz}, filepath=${output_filepath}"
}

main() {
    local tracing_dir="/sys/kernel/tracing"

    setup_colors
    sudo_check
    enable_required ${tracing_dir}

    output_dir="../output/"
    mkdir -p ${output_dir}

    seconds_to_run=2
    timestamp=$(date +"%Y%m%d_%H%M%S")
    output_file="${output_dir}/${timestamp}_scenario_${seconds_to_run}_s.trace"
    collect_trace ${tracing_dir} ${seconds_to_run} ${output_file}

    echo_info "trace collection finished"
}

main

