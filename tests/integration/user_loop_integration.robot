*** Settings ***
Documentation    User-loop integration tests

Library          RequestsLibrary
Library          Collections
Resource         ../setup/setup_keywords.robot
Resource         ../setup/teardown_keywords.robot
Resource         ../resources/user_loop_keywords.robot
Variables        ../setup/test_env.py

Suite Setup      Suite Setup
Suite Teardown   Suite Teardown
Test Setup       Clear Test Databases

*** Test Cases ***
Reject Swipe Removes Event And Updates MongoDB
    [Documentation]    Reject (left swipe) should stash, mark rejected, and remove from /events
    [Tags]    conversation

    ${timestamp}=    Get Timestamp
    ${conv_id}=      Set Variable    integration-reject-${timestamp}
    ${version_id}=   Set Variable    version-${timestamp}
    ${stash_id}=     Set Variable    ${EMPTY}

    TRY
        Insert Test Conversation    ${conv_id}    ${version_id}    maybe_anomaly=true
        Insert Test Audio Chunk    ${conv_id}    0    mock audio data

        ${response}=    GET On Session    api    /api/user-loop/events    expected_status=200
        ${events_before}=    Set Variable    ${response.json()}
        Should Not Be Empty    ${events_before}

        ${found}=    Set Variable    ${False}
        FOR    ${event}    IN    @{events_before}
            IF    '${event}[conversation_id]' == '${conv_id}' and '${event}[version_id]' == '${version_id}'
                ${found}=    Set Variable    ${True}
            END
        END
        Should Be True    ${found}    msg=Expected inserted anomaly to be present before reject

        ${body}=    Create Dictionary
        ...    transcript_version_id=${version_id}
        ...    conversation_id=${conv_id}
        ...    reason=Integration test false positive

        ${response}=    POST On Session    api    /api/user-loop/reject    json=${body}    expected_status=200
        ${result}=      Set Variable    ${response.json()}
        Should Be Equal    ${result}[status]    success
        Should Not Be Empty    ${result}[stash_id]
        ${stash_id}=    Set Variable    ${result}[stash_id]

        ${conv}=    Get Test Conversation    ${conv_id}
        ${maybe_anomaly}=    Get From Dictionary    ${conv}[transcript_versions][0]    maybe_anomaly
        Should Be Equal As Strings    ${maybe_anomaly}    rejected
        ${rejected_at}=    Get From Dictionary    ${conv}[transcript_versions][0]    rejected_at
        Should Not Be Empty    ${rejected_at}

        ${stash}=    Get Training Stash Entry    ${stash_id}
        Should Not Be Empty    ${stash}
        ${audio_chunks}=    Get From Dictionary    ${stash}    audio_chunks
        Should Not Be Empty    ${audio_chunks}

        ${response}=    GET On Session    api    /api/user-loop/events    expected_status=200
        ${events_after}=    Set Variable    ${response.json()}
        ${still_present}=    Set Variable    ${False}
        FOR    ${event}    IN    @{events_after}
            IF    '${event}[conversation_id]' == '${conv_id}' and '${event}[version_id]' == '${version_id}'
                ${still_present}=    Set Variable    ${True}
            END
        END
        Should Be True    ${still_present} == False    msg=Rejected anomaly should not reappear in /events
    FINALLY
        Run Keyword And Ignore Error    Delete Test Conversation    ${conv_id}
        IF    '${stash_id}' != '${EMPTY}'
            Run Keyword And Ignore Error    Delete Training Stash Entry    ${stash_id}
        END
    END

Accept Swipe Removes Event And Updates MongoDB
    [Documentation]    Accept (right swipe) should mark verified and remove from /events
    [Tags]    conversation

    ${timestamp}=    Get Timestamp
    ${conv_id}=      Set Variable    integration-accept-${timestamp}
    ${version_id}=   Set Variable    version-${timestamp}

    TRY
        Insert Test Conversation    ${conv_id}    ${version_id}    maybe_anomaly=true

        ${response}=    GET On Session    api    /api/user-loop/events    expected_status=200
        ${events_before}=    Set Variable    ${response.json()}
        Should Not Be Empty    ${events_before}

        ${found}=    Set Variable    ${False}
        FOR    ${event}    IN    @{events_before}
            IF    '${event}[conversation_id]' == '${conv_id}' and '${event}[version_id]' == '${version_id}'
                ${found}=    Set Variable    ${True}
            END
        END
        Should Be True    ${found}    msg=Expected inserted anomaly to be present before accept

        ${body}=    Create Dictionary
        ...    transcript_version_id=${version_id}
        ...    conversation_id=${conv_id}

        ${response}=    POST On Session    api    /api/user-loop/accept    json=${body}    expected_status=200
        ${result}=      Set Variable    ${response.json()}
        Should Be Equal    ${result}[status]    success
        Should Be Equal    ${result}[message]    Verified transcript

        ${conv}=    Get Test Conversation    ${conv_id}
        ${maybe_anomaly}=    Get From Dictionary    ${conv}[transcript_versions][0]    maybe_anomaly
        Should Be Equal As Strings    ${maybe_anomaly}    verified
        ${verified_at}=    Get From Dictionary    ${conv}[transcript_versions][0]    verified_at
        Should Not Be Empty    ${verified_at}

        ${response}=    GET On Session    api    /api/user-loop/events    expected_status=200
        ${events_after}=    Set Variable    ${response.json()}
        ${still_present}=    Set Variable    ${False}
        FOR    ${event}    IN    @{events_after}
            IF    '${event}[conversation_id]' == '${conv_id}' and '${event}[version_id]' == '${version_id}'
                ${still_present}=    Set Variable    ${True}
            END
        END
        Should Be True    ${still_present} == False    msg=Verified anomaly should not reappear in /events
    FINALLY
        Run Keyword And Ignore Error    Delete Test Conversation    ${conv_id}
    END

Multiple Anomalies Are Filtered By Status
    [Documentation]    Only maybe_anomaly=true is returned; verified/rejected are filtered
    [Tags]    conversation

    ${timestamp}=    Get Timestamp
    ${conv_true}=    Set Variable    multi-true-${timestamp}
    ${conv_ver}=     Set Variable    multi-verified-${timestamp}
    ${conv_rej}=     Set Variable    multi-rejected-${timestamp}

    TRY
        Insert Test Conversation    ${conv_true}    v-true-${timestamp}    maybe_anomaly=true
        Insert Test Conversation    ${conv_ver}     v-verified-${timestamp}    maybe_anomaly=verified
        Insert Test Conversation    ${conv_rej}     v-rejected-${timestamp}    maybe_anomaly=rejected

        ${response}=    GET On Session    api    /api/user-loop/events    expected_status=200
        ${events}=      Set Variable    ${response.json()}

        ${found_true}=    Set Variable    ${False}
        FOR    ${event}    IN    @{events}
            IF    '${event}[conversation_id]' == '${conv_true}'
                ${found_true}=    Set Variable    ${True}
                Should Be Equal    ${event}[version_id]    v-true-${timestamp}
            END
            Should Not Be Equal    ${event}[conversation_id]    ${conv_ver}
            Should Not Be Equal    ${event}[conversation_id]    ${conv_rej}
        END
        Should Be True    ${found_true}    msg=Expected maybe_anomaly=true conversation to be returned
    FINALLY
        Run Keyword And Ignore Error    Delete Test Conversation    ${conv_true}
        Run Keyword And Ignore Error    Delete Test Conversation    ${conv_ver}
        Run Keyword And Ignore Error    Delete Test Conversation    ${conv_rej}
    END

Deleted Conversations Are Not Returned
    [Documentation]    Conversations with deleted=true are filtered from /events
    [Tags]    conversation

    ${timestamp}=    Get Timestamp
    ${conv_id}=      Set Variable    deleted-conv-${timestamp}
    ${version_id}=   Set Variable    v-${timestamp}

    TRY
        Insert Test Conversation    ${conv_id}    ${version_id}    maybe_anomaly=true
        Mark Test Conversation Deleted    ${conv_id}    ${True}

        ${response}=    GET On Session    api    /api/user-loop/events    expected_status=200
        ${events}=      Set Variable    ${response.json()}
        ${still_present}=    Set Variable    ${False}
        FOR    ${event}    IN    @{events}
            IF    '${event}[conversation_id]' == '${conv_id}'
                ${still_present}=    Set Variable    ${True}
            END
        END
        Should Be True    ${still_present} == False    msg=Deleted conversations must not be returned by /events
    FINALLY
        Run Keyword And Ignore Error    Delete Test Conversation    ${conv_id}
    END
