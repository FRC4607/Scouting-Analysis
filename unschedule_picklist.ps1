Unregister-ScheduledTask -TaskName "FRC4607-Picklist" -Confirm:$false

# Set lid-close to shut down (plugged in and on battery)
powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 3
powercfg /setdcvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 3
powercfg /setactive SCHEME_CURRENT

Write-Host "Scheduled task 'FRC4607-Picklist' removed."
Write-Host "Lid-close will now shut down the laptop."
