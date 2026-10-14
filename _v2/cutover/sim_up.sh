#!/bin/bash
# same steps as development_full_checker.sh (simulator part), for the local sign-in proof
cd ~/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2
UDID=C0A21713-3953-4EF9-906D-A332CAAA1683
xcrun simctl boot $UDID >/dev/null 2>&1 || true; open -a Simulator
( cd odin_app && flutter build ios --simulator --debug --dart-define=ODIN_FORCE_ENV=phase2 > ../workspace/logs/app_ios.log 2>&1 )
APP=odin_app/build/ios/iphonesimulator/Runner.app
BID="$(/usr/libexec/PlistBuddy -c 'Print CFBundleIdentifier' "$APP/Info.plist")"
xcrun simctl install $UDID "$APP" && xcrun simctl launch $UDID "$BID" && echo "SIM APP LAUNCHED $BID"
