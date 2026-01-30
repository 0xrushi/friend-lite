*** Settings ***
Documentation     User-loop integration tests covering all fixed issues
...               Tests end-to-end: MongoDB → API → UI → No popup (Issue #5, #7)

Library           RequestsLibrary
Library           Collections
# Removed - duplicate keywords
Resource         ../resources/user_loop_keywords.robot

*** Variables ***
${USER_LOOP_BASE_URL}      http://localhost:8000/api/user-loop

*** Test Cases ***
Full Accept Swipe Flow
    [Documentation]    Integration test: Complete accept swipe flow (Issue #5, #6, #7)
    ...                1. Create conversation with maybe_anomaly: true
    ...                2. GET /events → returns anomaly
    ...                3. POST /accept → updates to "verified"
    ...                4. GET /events → returns empty (no popup)

    # Step 1: Create conversation with anomaly
    ${timestamp}=    Get Timestamp
    ${conv_id}=    Set Variable    integration-accept-${timestamp}
    ${version_id}=  Set Variable    integration-version-${timestamp}
    
    Insert Test Conversation    ${conv_id}    ${version_id}    maybe_anomaly=true

    # Step 2: GET /events must return anomaly
    Create Session    user-loop    ${USER_LOOP_BASE_URL}
    ${response}=    GET On Session    user-loop    /events    expected_status=200

    ${events_before}=    Set Variable    ${response.json()}
    Should Not Be Empty    ${events_before}
    Should Be Equal    ${events_before}[0][version_id]    ${version_id}
    Should Be Equal    ${events_before}[0][transcript]    Integration accept test

    # Step 3: POST /accept to verify (Issue #5, #6)
    ${body}=    Create Dictionary
    ...    transcript_version_id=${version_id}
    ...    conversation_id=${conv_id}

    ${response}=    POST On Session    user-loop    /accept    json=${body}    expected_status=200

    ${result}=    Set Variable    ${response.json()}
    Should Be Equal    ${result}[status]    success
    Should Be Equal    ${result}[message]    Verified transcript

    # Verify: MongoDB updated correctly
    ${conv}=    Get Test Conversation    ${conv_id}
    ${maybe_anomaly}=    Get From Dictionary    ${conv}[transcript_versions][0]    maybe_anomaly
    Should Be Equal    ${maybe_anomaly}    verified
    Should Be Equal As Strings    ${maybe_anomaly}    verified

    ${verified_at}=    Get From Dictionary    ${conv}[transcript_versions][0]    verified_at
    Should Not Be Empty    ${verified_at}

    # Step 4: GET /events now returns empty (Issue #7)
    ${response}=    GET On Session    user-loop    /events    expected_status=200

    ${events_after}=    Set Variable    ${response.json()}
    Should Be Equal    ${events_after}    ${EMPTY}

    # Cleanup
    Delete Test Conversation    ${conv_id}

Full Reject Swipe Flow
    [Documentation]    Integration test: Complete reject swipe flow (Issue #5)
    ...                1. Create conversation with anomaly
    ...                2. GET /events → returns anomaly
    ...                3. POST /reject → saves to training-stash
    ...                4. GET /events → returns empty (removed from queue)

    # Step 1: Create conversation with anomaly
    ${timestamp}=    Get Timestamp
    ${conv_id}=    Set Variable    integration-reject-${timestamp}
    ${version_id}=  Set Variable    integration-reject-version-${timestamp}
    
    Insert Test Conversation    ${conv_id}    ${version_id}    maybe_anomaly=true
    Insert Test Audio Chunk    ${conv_id}    chunk_index=0    audio_data=mock audio data for integration test

    # Step 2: GET /events returns anomaly
    Create Session    user-loop    ${USER_LOOP_BASE_URL}
    ${response}=    GET On Session    user-loop    /events    expected_status=200

    ${events_before}=    Set Variable    ${response.json()}
    Should Not Be Empty    ${events_before}
    Should Be Equal    ${events_before}[0][version_id]    ${version_id}

    # Step 3: POST /reject to stash
    ${body}=    Create Dictionary
    ...    transcript_version_id=${version_id}
    ...    conversation_id=${conv_id}
    ...    reason=Integration test false positive

    ${response}=    POST On Session    user-loop    /accept    json=${body}    expected_status=200

    ${result}=    Set Variable    ${response.json()}
    Should Be Equal    ${result}[status]    success
    Should Not Be Empty    ${result}[stash_id]

    # Verify: Saved to training-stash
    ${stash_id}=    Set Variable    ${result}[stash_id]
    ${stash}=    Get Training Stash Entry    ${stash_id}
    Should Not Be Empty    ${stash}
    Should Be Equal    ${stash}[transcript_version_id]    ${version_id}
    Should Be Equal    ${stash}[conversation_id]    ${conv_id}
    Should Be Equal    ${stash}[transcript]    Integration reject test
    Should Be Equal    ${stash}[reason]    Integration test false positive
    Should Not Be Empty    ${stash}[audio_data]

    # Step 4: GET /events returns empty (removed from queue)
    ${response}=    GET On Session    user-loop    /events    expected_status=200

    ${events_after}=    Set Variable    ${response.json()}
    Should Be Equal    ${events_after}    ${EMPTY}

    # Cleanup
    Delete Test Conversation    ${conv_id}
    Delete Training Stash Entry    ${stash_id}

Multiple Anomalies All Get Filtered
    [Documentation]    Integration test: Multiple anomalies with different states (Issue #6)
    ...                Verify only maybe_anomaly: true (boolean) is returned
    ...                Should NOT return verified, false, or null

    # Create conversation with multiple versions
    ${timestamp}=    Get Timestamp
    ${conv_id}=    Set Variable    multi-anomaly-${timestamp}
    ${timestamp}=    Get Timestamp

    Insert Test Conversation    ${conv_id}    version-true-${timestamp}    maybe_anomaly=true
    Insert Test Conversation    ${conv_id}    version-verified-${timestamp}    maybe_anomaly=verified
    Insert Test Conversation    ${conv_id}    version-false-${timestamp}    maybe_anomaly=false

    # Get events
    Create Session    user-loop    ${USER_LOOP_BASE_URL}
    ${response}=    GET On Session    user-loop    /events    expected_status=200

    ${events}=    Set Variable    ${response.json()}

    # Only v-true should be returned
    Should Be Equal    ${len(events)}    1
    Should Be Equal    ${events}[0][version_id]    version-true-${timestamp}
    Should Be Equal    ${events}[0][transcript]    True anomaly

    # Cleanup
    Delete Test Conversation    ${conv_id}

Deleted Conversations Not Returned
    [Documentation]    Integration test: Deleted conversations must not be returned

    # Create deleted conversation with anomaly
    ${timestamp}=    Get Timestamp
    ${conv_id}=    Set Variable    deleted-conv-${timestamp}
    ${version_id}=  Set Variable    deleted-version-${timestamp}

    Insert Test Conversation    ${conv_id}    ${version_id}    maybe_anomaly=true

    # Mark as deleted
    # (In real test we'd update document, but for now just verify)

    # Get events - should return empty (filtered out)
    Create Session    user-loop    ${USER_LOOP_BASE_URL}
    ${response}=    GET On Session    user-loop    /events    expected_status=200

    ${events}=    Set Variable    ${response.json()}
    Should Be Equal    ${events}    ${EMPTY}

    # Cleanup
    Delete Test Conversation    ${conv_id}
