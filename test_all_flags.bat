@echo off
setlocal enabledelayedexpansion

echo 🧪 HFOrchestra Comprehensive Flag Tester
echo 🔍 ENFORCED: All file-based tasks MUST use Magika
echo ============================================================

:: Create reports directory
if not exist "reports" mkdir reports

:: Get timestamp for report files
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "timestamp=%dt:~0,8%_%dt:~8,6%"

:: Initialize counters
set "total=0"
set "passed=0"
set "failed=0"

:: Create report files
echo HFOrchestra Flag Test Report > "reports\flag_test_report_%timestamp%.txt"
echo Generated: %date% %time% >> "reports\flag_test_report_%timestamp%.txt"
echo ============================================================ >> "reports\flag_test_report_%timestamp%.txt"
echo. >> "reports\flag_test_report_%timestamp%.txt"

echo { > "reports\flag_test_results_%timestamp%.json"
echo   "timestamp": "%timestamp%", >> "reports\flag_test_results_%timestamp%.json"
echo   "summary": { >> "reports\flag_test_results_%timestamp%.json"
echo     "total_tests": 0, >> "reports\flag_test_results_%timestamp%.json"
echo     "successful": 0, >> "reports\flag_test_results_%timestamp%.json"
echo     "failed": 0 >> "reports\flag_test_results_%timestamp%.json"
echo   }, >> "reports\flag_test_results_%timestamp%.json"
echo   "results": { >> "reports\flag_test_results_%timestamp%.json"

:: Test text-based tasks
echo.
echo ============================================================
echo Testing Text-Based Tasks
echo ============================================================

:: Text Classification
call :test_flag "text-classification" "Classify text into categories" "text" "Analyze the sentiment of this text"

:: Text Generation
call :test_flag "text-generation" "Generate text content" "text" "Continue this text naturally"

:: Summarization
call :test_flag "summarization" "Summarize long text" "text" "Summarize this content"

:: Translation
call :test_flag "translation" "Translate between languages" "text" "Translate to Spanish"

:: Question Answering
call :test_flag "question-answering" "Answer questions" "text" "What is this about?"

:: Sentiment Analysis
call :test_flag "sentiment" "Analyze sentiment" "text" "What is the sentiment of this text?"

:: Named Entity Recognition
call :test_flag "ner" "Named Entity Recognition" "text" "Extract named entities from this text"

:: Spam Detection
call :test_flag "spam-detection" "Detect spam content" "text" "Is this spam or legitimate content?"

:: Malware Text Detection
call :test_flag "malware-text-detection" "Detect malicious text" "text" "Does this contain malicious content?"

:: PII Detection
call :test_flag "pii-detection" "Detect personal information" "text" "Find any personal information in this text"

:: Hate Speech Detection
call :test_flag "hate-speech-detection" "Detect hate speech" "text" "Check this message for hate speech"

:: Emotion Detection
call :test_flag "emotion-detection" "Detect emotions in text" "text" "What emotion is expressed?"

:: Image-based tasks
echo.
echo ============================================================
echo Testing Image-Based Tasks
echo ============================================================

:: Image Classification
call :test_flag "image-classification" "Classify images" "image" "What is in this image?"

:: Object Detection
call :test_flag "object-detection" "Detect objects in images" "image" "What objects can you see in this image?"

:: Visual Question Answering
call :test_flag "visual-question-answering" "Answer questions about images" "image" "What is the main subject of this image?"

:: Audio-based tasks
echo.
echo ============================================================
echo Testing Audio-Based Tasks
echo ============================================================

:: Automatic Speech Recognition
call :test_flag "automatic-speech-recognition" "Convert speech to text" "audio" "Transcribe this audio"

:: Audio Classification
call :test_flag "audio-classification" "Classify audio content" "audio" "What type of audio is this?"

:: Voice Activity Detection
call :test_flag "voice-activity-detection" "Detect voice activity" "audio" "Detect speech activity in this audio"

:: Emotion Recognition
call :test_flag "emotion-recognition" "Recognize emotions in audio" "audio" "What emotion is expressed in this audio?"

:: Video-based tasks
echo.
echo ============================================================
echo Testing Video-Based Tasks
echo ============================================================

:: Video Classification
call :test_flag "video-classification" "Classify videos" "video" "What type of video is this?"

:: Document-based tasks
echo.
echo ============================================================
echo Testing Document-Based Tasks
echo ============================================================

:: Document Question Answering
call :test_flag "document-question-answering" "Answer questions about documents" "document" "Answer questions about this document"

:: Table Question Answering
call :test_flag "table-question-answering" "Answer questions about tables" "document" "Answer questions about this table"

:: Analysis tasks
echo.
echo ============================================================
echo Testing Analysis Tasks
echo ============================================================

:: PE Header Extraction
call :test_flag "pe-header-extraction" "Extract PE headers" "analysis" "Extract PE headers from this executable"

:: Feature Extraction
call :test_flag "feature-extraction" "Extract features" "analysis" "Extract features from this content"

:: Standalone tasks (no file needed)
echo.
echo ============================================================
echo Testing Standalone Tasks
echo ============================================================

:: Stats
call :test_flag_standalone "stats" "Show database statistics"

:: Tasks
call :test_flag_standalone "tasks" "List available tasks"

:: Update
call :test_flag_standalone "update" "Update database"

:: Decision Stats
call :test_flag_standalone "decision-stats" "Show decision statistics"

:: Novel AI Stats
call :test_flag_standalone "novel-ai-stats" "Show novel AI statistics"

:: Performance Stats
call :test_flag_standalone "performance-stats" "Show performance statistics"

:: Cache Stats
call :test_flag_standalone "cache-stats" "Show cache statistics"

:: Clear Cache
call :test_flag_standalone "clearcache" "Clear cache"

:: Analytics Demo
call :test_flag_standalone "analytics-demo" "Run analytics demo"

:: Model Ranking
call :test_flag_standalone "model-ranking" "Show model rankings"

:: Model Recommendations
call :test_flag_standalone "model-recommendations" "Get model recommendations"

:: Demo HyDE
call :test_flag_standalone "demo-hyde" "Run HyDE demo"

:: Plan
call :test_flag_standalone "plan" "Create execution plan"

:: Judge
call :test_flag_standalone "judge" "Judge model outputs"

:: Score
call :test_flag_standalone "score" "Score model performance"

:: Close JSON file
echo   } >> "reports\flag_test_results_%timestamp%.json"
echo } >> "reports\flag_test_results_%timestamp%.json"

:: Update summary in JSON
powershell -Command "(Get-Content 'reports\flag_test_results_%timestamp%.json') -replace '\"total_tests\": 0', '\"total_tests\": %total%' -replace '\"successful\": 0', '\"successful\": %passed%' -replace '\"failed\": 0', '\"failed\": %failed%' | Set-Content 'reports\flag_test_results_%timestamp%.json'"

:: Print final summary
echo.
echo ============================================================
echo 📊 FINAL SUMMARY
echo ============================================================
echo Total Tests: %total%
echo ✅ Passed: %passed%
echo ❌ Failed: %failed%
set /a "success_rate=(%passed% * 100) / %total%"
echo 📈 Success Rate: %success_rate%%%

:: Add summary to report
echo. >> "reports\flag_test_report_%timestamp%.txt"
echo ============================================================ >> "reports\flag_test_report_%timestamp%.txt"
echo FINAL SUMMARY >> "reports\flag_test_report_%timestamp%.txt"
echo ============================================================ >> "reports\flag_test_report_%timestamp%.txt"
echo Total Tests: %total% >> "reports\flag_test_report_%timestamp%.txt"
echo Passed: %passed% >> "reports\flag_test_report_%timestamp%.txt"
echo Failed: %failed% >> "reports\flag_test_report_%timestamp%.txt"
echo Success Rate: %success_rate%%% >> "reports\flag_test_report_%timestamp%.txt"

echo.
echo 📄 Reports saved to:
echo    reports\flag_test_report_%timestamp%.txt
echo    reports\flag_test_results_%timestamp%.json
echo.
echo 🎉 Testing completed!
pause
exit /b

:test_flag
set "flag=%~1"
set "description=%~2"
set "category=%~3"
set "prompt=%~4"
set /a "total+=1"

echo.
echo 🧪 Test %total%: --%flag%
echo 📝 Description: %description%
echo 📂 Category: %category%
echo 💬 Using prompt: %prompt%

:: Check if test file exists
set "test_file="
if "%category%"=="text" set "test_file=c:\testfiles\file.txt"
if "%category%"=="image" set "test_file=c:\testfiles\cow.jfif"
if "%category%"=="audio" set "test_file=c:\testfiles\harvard.wav"
if "%category%"=="video" set "test_file=c:\testfiles\sample.mp4"
if "%category%"=="document" set "test_file=c:\testfiles\sample.pdf"
if "%category%"=="analysis" set "test_file=c:\testfiles\sample.exe"

if defined test_file (
    echo 📁 Using file: %test_file%
    echo 🔍 [MAGIKA] File-based task - AI-powered file type detection will be used
    echo 🚀 Running: python main.py --%flag% --file "%test_file%" --prompt "%prompt%" --use-magika --verbose
    
    :: Run the command and capture output
    python main.py --%flag% --file "%test_file%" --prompt "%prompt%" --use-magika --verbose > "temp_output.txt" 2>&1
    set "exit_code=!errorlevel!"
) else (
    echo 🚀 Running: python main.py --%flag% --prompt "%prompt%" --verbose
    
    :: Run the command and capture output
    python main.py --%flag% --prompt "%prompt%" --verbose > "temp_output.txt" 2>&1
    set "exit_code=!errorlevel!"
)

:: Check if command succeeded
if !exit_code! equ 0 (
    echo ✅ SUCCESS: %flag% completed
    set /a "passed+=1"
    set "status=SUCCESS"
    set "magika_status=✅ MAGIKA USED"
) else (
    echo ❌ FAILED: %flag% - Command failed with return code !exit_code!
    set /a "failed+=1"
    set "status=FAILED"
    set "magika_status=❌ NO MAGIKA"
)

:: Check for Magika usage in output
findstr /i "magika" "temp_output.txt" >nul
if !errorlevel! equ 0 (
    echo 🔍 [MAGIKA] Confirmed: AI-powered file type detection was used
    set "magika_status=✅ MAGIKA USED"
) else (
    echo ⚠️ [MAGIKA] Warning: No explicit Magika usage detected in output
    set "magika_status=⚠️ NO MAGIKA"
)

:: Add to report
echo %flag%: %status% - %magika_status% >> "reports\flag_test_report_%timestamp%.txt"
if defined test_file (
    echo   File: %test_file% >> "reports\flag_test_report_%timestamp%.txt"
) else (
    echo   No file required >> "reports\flag_test_report_%timestamp%.txt"
)
if defined test_file (
    echo   Command: python main.py --%flag% --file "%test_file%" --prompt "%prompt%" --use-magika --verbose >> "reports\flag_test_report_%timestamp%.txt"
) else (
    echo   Command: python main.py --%flag% --prompt "%prompt%" --verbose >> "reports\flag_test_report_%timestamp%.txt"
)
echo. >> "reports\flag_test_report_%timestamp%.txt"

:: Add to JSON
echo     "%flag%": { >> "reports\flag_test_results_%timestamp%.json"
echo       "flag": "%flag%", >> "reports\flag_test_results_%timestamp%.json"
echo       "description": "%description%", >> "reports\flag_test_results_%timestamp%.json"
echo       "category": "%category%", >> "reports\flag_test_results_%timestamp%.json"
echo       "success": %exit_code% == 0, >> "reports\flag_test_results_%timestamp%.json"
echo       "return_code": !exit_code!, >> "reports\flag_test_results_%timestamp%.json"
echo       "magika_used": "%magika_status%" == "✅ MAGIKA USED" >> "reports\flag_test_results_%timestamp%.json"
echo     }, >> "reports\flag_test_results_%timestamp%.json"

:: Clean up temp file
del "temp_output.txt" >nul 2>&1
exit /b

:test_flag_standalone
set "flag=%~1"
set "description=%~2"
set /a "total+=1"

echo.
echo 🧪 Test %total%: --%flag%
echo 📝 Description: %description%
echo 📂 Category: standalone
echo 🚀 Running: python main.py --%flag% --verbose

:: Run the command and capture output
python main.py --%flag% --verbose > "temp_output.txt" 2>&1
set "exit_code=!errorlevel!"

:: Check if command succeeded
if !exit_code! equ 0 (
    echo ✅ SUCCESS: %flag% completed
    set /a "passed+=1"
    set "status=SUCCESS"
) else (
    echo ❌ FAILED: %flag% - Command failed with return code !exit_code!
    set /a "failed+=1"
    set "status=FAILED"
)

:: Add to report
echo %flag%: %status% - STANDALONE TASK >> "reports\flag_test_report_%timestamp%.txt"
echo   No file required >> "reports\flag_test_report_%timestamp%.txt"
echo   Command: python main.py --%flag% --verbose >> "reports\flag_test_report_%timestamp%.txt"
echo. >> "reports\flag_test_report_%timestamp%.txt"

:: Add to JSON
echo     "%flag%": { >> "reports\flag_test_results_%timestamp%.json"
echo       "flag": "%flag%", >> "reports\flag_test_results_%timestamp%.json"
echo       "description": "%description%", >> "reports\flag_test_results_%timestamp%.json"
echo       "category": "standalone", >> "reports\flag_test_results_%timestamp%.json"
echo       "success": %exit_code% == 0, >> "reports\flag_test_results_%timestamp%.json"
echo       "return_code": !exit_code!, >> "reports\flag_test_results_%timestamp%.json"
echo       "magika_used": false >> "reports\flag_test_results_%timestamp%.json"
echo     }, >> "reports\flag_test_results_%timestamp%.json"

:: Clean up temp file
del "temp_output.txt" >nul 2>&1
exit /b
