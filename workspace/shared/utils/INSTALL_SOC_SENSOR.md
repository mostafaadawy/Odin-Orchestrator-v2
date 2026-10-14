# Install the 24/7 SOC sensor (owner-approved — it writes to the VM)

Read-only, resource-capped (CPUQuota 4%, MemoryMax 48M, idle IO, nice 19) so it never disturbs the sites on
an 8GB VM. It only appends a compact JSON line every 5 min; the desktop agents analyze it (catch-up).

    scp infra/soc_sensor.sh mostafa@<vm>:/home/mostafa/soc-sensor/soc_sensor.sh
    ssh mostafa@<vm> 'chmod +x /home/mostafa/soc-sensor/soc_sensor.sh'
    scp infra/soc-sensor.service infra/soc-sensor.timer mostafa@<vm>:/tmp/
    ssh mostafa@<vm> 'sudo mv /tmp/soc-sensor.* /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable --now soc-sensor.timer'

Uninstall: `sudo systemctl disable --now soc-sensor.timer`. Nothing else on the VM is touched.
