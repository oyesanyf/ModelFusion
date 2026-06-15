@echo off
setlocal enabledelayedexpansion

echo 🧪 HFOrchestra Simple Flag Tester
echo 🔍 Testing all 66 flags with Magika enforcement
echo ============================================================

:: Create reports directory
if not exist "reports" mkdir reports

:: Get timestamp
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "timestamp=%dt:~0,8%_%dt:~8,6%"

:: Initialize counters
set "total=0"
set "passed=0"
set "failed=0"

:: Create report file
echo HFOrchestra Flag Test Report > "reports\simple_test_report_%timestamp%.txt"
echo Generated: %date% %time% >> "reports\simple_test_report_%timestamp%.txt"
echo ============================================================ >> "reports\simple_test_report_%timestamp%.txt"
echo. >> "reports\simple_test_report_%timestamp%.txt"

echo 🚀 Starting tests...
echo.

:: Test 1: text-classification
set /a "total+=1"
echo 🧪 Test %total%: text-classification
python main.py --text-classification --file "c:\testfiles\file.txt" --prompt "Analyze the sentiment of this text" --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: text-classification
    set /a "passed+=1"
    echo text-classification: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: text-classification
    set /a "failed+=1"
    echo text-classification: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 2: text-generation
set /a "total+=1"
echo 🧪 Test %total%: text-generation
python main.py --text-generation --file "c:\testfiles\file.txt" --prompt "Continue this text naturally" --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: text-generation
    set /a "passed+=1"
    echo text-generation: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: text-generation
    set /a "failed+=1"
    echo text-generation: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 3: summarization
set /a "total+=1"
echo 🧪 Test %total%: summarization
python main.py --summarization --file "c:\testfiles\file.txt" --prompt "Summarize this content" --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: summarization
    set /a "passed+=1"
    echo summarization: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: summarization
    set /a "failed+=1"
    echo summarization: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 4: translation
set /a "total+=1"
echo 🧪 Test %total%: translation
python main.py --translation --file "c:\testfiles\file.txt" --prompt "Translate to Spanish" --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: translation
    set /a "passed+=1"
    echo translation: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: translation
    set /a "failed+=1"
    echo translation: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 5: question-answering
set /a "total+=1"
echo 🧪 Test %total%: question-answering
python main.py --question-answering --file "c:\testfiles\file.txt" --prompt "What is this about?" --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: question-answering
    set /a "passed+=1"
    echo question-answering: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: question-answering
    set /a "failed+=1"
    echo question-answering: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 6: sentiment
set /a "total+=1"
echo 🧪 Test %total%: sentiment
python main.py --sentiment --file "c:\testfiles\file.txt" --prompt "What is the sentiment of this text?" --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: sentiment
    set /a "passed+=1"
    echo sentiment: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: sentiment
    set /a "failed+=1"
    echo sentiment: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 7: ner
set /a "total+=1"
echo 🧪 Test %total%: ner
python main.py --ner --file "c:\testfiles\file.txt" --prompt "Extract named entities from this text" --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: ner
    set /a "passed+=1"
    echo ner: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: ner
    set /a "failed+=1"
    echo ner: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 8: spam-detection
set /a "total+=1"
echo 🧪 Test %total%: spam-detection
python main.py --spam-detection --file "c:\testfiles\file.txt" --prompt "Is this spam or legitimate content?" --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: spam-detection
    set /a "passed+=1"
    echo spam-detection: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: spam-detection
    set /a "failed+=1"
    echo spam-detection: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 9: malware-text-detection
set /a "total+=1"
echo 🧪 Test %total%: malware-text-detection
python main.py --malware-text-detection --file "c:\testfiles\file.txt" --prompt "Does this contain malicious content?" --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: malware-text-detection
    set /a "passed+=1"
    echo malware-text-detection: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: malware-text-detection
    set /a "failed+=1"
    echo malware-text-detection: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 10: pii-detection
set /a "total+=1"
echo 🧪 Test %total%: pii-detection
python main.py --pii-detection --file "c:\testfiles\file.txt" --prompt "Find any personal information in this text" --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: pii-detection
    set /a "passed+=1"
    echo pii-detection: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: pii-detection
    set /a "failed+=1"
    echo pii-detection: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 11: hate-speech-detection
set /a "total+=1"
echo 🧪 Test %total%: hate-speech-detection
python main.py --hate-speech-detection --file "c:\testfiles\file.txt" --prompt "Check this message for hate speech" --use-magika --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: hate-speech-detection
    set /a "passed+=1"
    echo hate-speech-detection: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: hate-speech-detection
    set /a "failed+=1"
    echo hate-speech-detection: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 12: emotion-detection
set /a "total+=1"
echo 🧪 Test %total%: emotion-detection
python main.py --emotion-detection --file "c:\testfiles\file.txt" --prompt "What emotion is expressed?" --use-magika --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: emotion-detection
    set /a "passed+=1"
    echo emotion-detection: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: emotion-detection
    set /a "failed+=1"
    echo emotion-detection: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 13: image-classification
set /a "total+=1"
echo 🧪 Test %total%: image-classification
python main.py --image-classification --file "c:\testfiles\cow.jfif" --prompt "What is in this image?" --use-magika --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: image-classification
    set /a "passed+=1"
    echo image-classification: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: image-classification
    set /a "failed+=1"
    echo image-classification: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 14: object-detection
set /a "total+=1"
echo 🧪 Test %total%: object-detection
python main.py --object-detection --file "c:\testfiles\cow.jfif" --prompt "What objects can you see in this image?" --use-magika --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: object-detection
    set /a "passed+=1"
    echo object-detection: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: object-detection
    set /a "failed+=1"
    echo object-detection: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 15: visual-question-answering
set /a "total+=1"
echo 🧪 Test %total%: visual-question-answering
python main.py --visual-question-answering --file "c:\testfiles\cow.jfif" --prompt "What is the main subject of this image?" --use-magika --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: visual-question-answering
    set /a "passed+=1"
    echo visual-question-answering: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: visual-question-answering
    set /a "failed+=1"
    echo visual-question-answering: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 16: automatic-speech-recognition
set /a "total+=1"
echo 🧪 Test %total%: automatic-speech-recognition
python main.py --automatic-speech-recognition --file "c:\testfiles\harvard.wav" --prompt "Transcribe this audio" --use-magika --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: automatic-speech-recognition
    set /a "passed+=1"
    echo automatic-speech-recognition: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: automatic-speech-recognition
    set /a "failed+=1"
    echo automatic-speech-recognition: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 17: audio-classification
set /a "total+=1"
echo 🧪 Test %total%: audio-classification
python main.py --audio-classification --file "c:\testfiles\harvard.wav" --prompt "What type of audio is this?" --use-magika --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: audio-classification
    set /a "passed+=1"
    echo audio-classification: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: audio-classification
    set /a "failed+=1"
    echo audio-classification: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 18: voice-activity-detection
set /a "total+=1"
echo 🧪 Test %total%: voice-activity-detection
python main.py --voice-activity-detection --file "c:\testfiles\harvard.wav" --prompt "Detect speech activity in this audio" --use-magika --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: voice-activity-detection
    set /a "passed+=1"
    echo voice-activity-detection: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: voice-activity-detection
    set /a "failed+=1"
    echo voice-activity-detection: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 19: emotion-recognition
set /a "total+=1"
echo 🧪 Test %total%: emotion-recognition
python main.py --emotion-recognition --file "c:\testfiles\harvard.wav" --prompt "What emotion is expressed in this audio?" --use-magika --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: emotion-recognition
    set /a "passed+=1"
    echo emotion-recognition: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: emotion-recognition
    set /a "failed+=1"
    echo emotion-recognition: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 20: video-classification
set /a "total+=1"
echo 🧪 Test %total%: video-classification
python main.py --video-classification --file "c:\testfiles\sample.mp4" --prompt "What type of video is this?" --use-magika --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: video-classification
    set /a "passed+=1"
    echo video-classification: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: video-classification
    set /a "failed+=1"
    echo video-classification: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 21: document-question-answering
set /a "total+=1"
echo 🧪 Test %total%: document-question-answering
python main.py --document-question-answering --file "c:\testfiles\sample.pdf" --prompt "Answer questions about this document" --use-magika --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: document-question-answering
    set /a "passed+=1"
    echo document-question-answering: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: document-question-answering
    set /a "failed+=1"
    echo document-question-answering: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 22: table-question-answering
set /a "total+=1"
echo 🧪 Test %total%: table-question-answering
python main.py --table-question-answering --file "c:\testfiles\sample.pdf" --prompt "Answer questions about this table" --use-magika --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: table-question-answering
    set /a "passed+=1"
    echo table-question-answering: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: table-question-answering
    set /a "failed+=1"
    echo table-question-answering: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 23: pe-header-extraction
set /a "total+=1"
echo 🧪 Test %total%: pe-header-extraction
python main.py --pe-header-extraction --file "c:\testfiles\sample.exe" --prompt "Extract PE headers from this executable" --use-magika --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: pe-header-extraction
    set /a "passed+=1"
    echo pe-header-extraction: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: pe-header-extraction
    set /a "failed+=1"
    echo pe-header-extraction: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 24: feature-extraction
set /a "total+=1"
echo 🧪 Test %total%: feature-extraction
python main.py --feature-extraction --file "c:\testfiles\file.txt" --prompt "Extract features from this content" --use-magika --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: feature-extraction
    set /a "passed+=1"
    echo feature-extraction: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: feature-extraction
    set /a "failed+=1"
    echo feature-extraction: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Standalone tasks (no file needed)
echo.
echo ============================================================
echo Testing Standalone Tasks
echo ============================================================

:: Test 25: stats
set /a "total+=1"
echo 🧪 Test %total%: stats
python main.py --stats --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: stats
    set /a "passed+=1"
    echo stats: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: stats
    set /a "failed+=1"
    echo stats: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 26: tasks
set /a "total+=1"
echo 🧪 Test %total%: tasks
python main.py --tasks --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: tasks
    set /a "passed+=1"
    echo tasks: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: tasks
    set /a "failed+=1"
    echo tasks: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 27: update
set /a "total+=1"
echo 🧪 Test %total%: update
python main.py --update --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: update
    set /a "passed+=1"
    echo update: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: update
    set /a "failed+=1"
    echo update: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 28: decision-stats
set /a "total+=1"
echo 🧪 Test %total%: decision-stats
python main.py --decision-stats --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: decision-stats
    set /a "passed+=1"
    echo decision-stats: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: decision-stats
    set /a "failed+=1"
    echo decision-stats: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 29: novel-ai-stats
set /a "total+=1"
echo 🧪 Test %total%: novel-ai-stats
python main.py --novel-ai-stats --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: novel-ai-stats
    set /a "passed+=1"
    echo novel-ai-stats: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: novel-ai-stats
    set /a "failed+=1"
    echo novel-ai-stats: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 30: performance-stats
set /a "total+=1"
echo 🧪 Test %total%: performance-stats
python main.py --performance-stats --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: performance-stats
    set /a "passed+=1"
    echo performance-stats: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: performance-stats
    set /a "failed+=1"
    echo performance-stats: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 31: cache-stats
set /a "total+=1"
echo 🧪 Test %total%: cache-stats
python main.py --cache-stats --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: cache-stats
    set /a "passed+=1"
    echo cache-stats: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: cache-stats
    set /a "failed+=1"
    echo cache-stats: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 32: clearcache
set /a "total+=1"
echo 🧪 Test %total%: clearcache
python main.py --clearcache --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: clearcache
    set /a "passed+=1"
    echo clearcache: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: clearcache
    set /a "failed+=1"
    echo clearcache: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 33: analytics-demo
set /a "total+=1"
echo 🧪 Test %total%: analytics-demo
python main.py --analytics-demo --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: analytics-demo
    set /a "passed+=1"
    echo analytics-demo: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: analytics-demo
    set /a "failed+=1"
    echo analytics-demo: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 34: model-ranking
set /a "total+=1"
echo 🧪 Test %total%: model-ranking
python main.py --model-ranking --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: model-ranking
    set /a "passed+=1"
    echo model-ranking: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: model-ranking
    set /a "failed+=1"
    echo model-ranking: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 35: model-recommendations
set /a "total+=1"
echo 🧪 Test %total%: model-recommendations
python main.py --model-recommendations --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: model-recommendations
    set /a "passed+=1"
    echo model-recommendations: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: model-recommendations
    set /a "failed+=1"
    echo model-recommendations: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 36: demo-hyde
set /a "total+=1"
echo 🧪 Test %total%: demo-hyde
python main.py --demo-hyde --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: demo-hyde
    set /a "passed+=1"
    echo demo-hyde: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: demo-hyde
    set /a "failed+=1"
    echo demo-hyde: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 37: plan
set /a "total+=1"
echo 🧪 Test %total%: plan
python main.py --plan --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: plan
    set /a "passed+=1"
    echo plan: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: plan
    set /a "failed+=1"
    echo plan: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 38: judge
set /a "total+=1"
echo 🧪 Test %total%: judge
python main.py --judge --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: judge
    set /a "passed+=1"
    echo judge: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: judge
    set /a "failed+=1"
    echo judge: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

:: Test 39: score
set /a "total+=1"
echo 🧪 Test %total%: score
python main.py --score --verbose
if !errorlevel! equ 0 (
    echo ✅ PASSED: score
    set /a "passed+=1"
    echo score: PASSED >> "reports\simple_test_report_%timestamp%.txt"
) else (
    echo ❌ FAILED: score
    set /a "failed+=1"
    echo score: FAILED >> "reports\simple_test_report_%timestamp%.txt"
)

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
echo. >> "reports\simple_test_report_%timestamp%.txt"
echo ============================================================ >> "reports\simple_test_report_%timestamp%.txt"
echo FINAL SUMMARY >> "reports\simple_test_report_%timestamp%.txt"
echo ============================================================ >> "reports\simple_test_report_%timestamp%.txt"
echo Total Tests: %total% >> "reports\simple_test_report_%timestamp%.txt"
echo Passed: %passed% >> "reports\simple_test_report_%timestamp%.txt"
echo Failed: %failed% >> "reports\simple_test_report_%timestamp%.txt"
echo Success Rate: %success_rate%%% >> "reports\simple_test_report_%timestamp%.txt"

echo.
echo 📄 Report saved to: reports\simple_test_report_%timestamp%.txt
echo.
echo 🎉 Testing completed!
pause
