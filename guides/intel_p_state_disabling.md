In some specific PC-s, `intel_pstate` is used by default, which blocks `cpu_frequency` related information collection. If you want to collect `schedutil` related stuff, you should do such stuff:

1. Open with your favourite editor `/etc/default/grub`:
```bash
sudo vim /etc/default/grub
```

2. Apply modifications to default commands:
Replace this line
```bash
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"
```
With this one:
```bash
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash intel_pstate=disable"
```

3. Then reboot for modifications to work:
```bash
sudo update-grub
sudo reboot
```
