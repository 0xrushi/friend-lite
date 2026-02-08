*** Settings ***
Resource         resources/user_loop_keywords.robot

*** Test Cases ***
Test Get Timestamp
    ${timestamp}=    Get Timestamp
    Log    Timestamp: ${timestamp}
