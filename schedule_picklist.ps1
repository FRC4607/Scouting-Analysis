$root = "C:\Users\ejmcc\Documents\FRC4607\Scouting-Analysis"

$action = New-ScheduledTaskAction -Execute "cmd.exe" `
  -Argument "/c cd /d $root && venv\Scripts\activate && run_picklist --event_key 2026mnmi2 --save --post"

$trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 30) `
  -Once -At "2026-04-10 09:00" -RepetitionDuration (New-TimeSpan -Hours 10)

Register-ScheduledTask -TaskName "FRC4607-Picklist" -Action $action -Trigger $trigger

# Keep laptop awake when lid is closed (plugged in and on battery)
powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
powercfg /setdcvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
powercfg /setactive SCHEME_CURRENT

Write-Host "Scheduled task 'FRC4607-Picklist' registered. Runs every 30 minutes from 9am to 7pm tomorrow."
Write-Host "Lid-close will no longer sleep the laptop."
Write-Host "To remove the task when done: Unregister-ScheduledTask -TaskName 'FRC4607-Picklist' -Confirm:`$false"
