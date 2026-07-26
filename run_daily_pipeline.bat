@echo off
setlocal

cd /d C:\stock-bot

if not exist C:\stock-bot\logs (
    mkdir C:\stock-bot\logs
)

echo ================================================== >> C:\stock-bot\logs\task_scheduler_output.log
echo STARTED: %date% %time% >> C:\stock-bot\logs\task_scheduler_output.log

C:\stock-bot\.venv\Scripts\python.exe C:\stock-bot\run_daily_pipeline.py >> C:\stock-bot\logs\task_scheduler_output.log 2>&1

set EXIT_CODE=%errorlevel%

echo FINISHED: %date% %time% >> C:\stock-bot\logs\task_scheduler_output.log
echo EXIT CODE: %EXIT_CODE% >> C:\stock-bot\logs\task_scheduler_output.log
echo ================================================== >> C:\stock-bot\logs\task_scheduler_output.log

exit /b %EXIT_CODE%