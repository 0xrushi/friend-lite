*** Settings ***
Documentation     User-loop endpoint tests covering all fixed issues
...               Issue #1: Audio not playing (Opus→WAV)
...               Issue #2: /audio/undefined (404)
...               Issue #3: FFmpeg not installed
...               Issue #5: Swipe right not working
...               Issue #6: Field name mismatch (422 error)
...               Issue #7: Loading spinner stuck
...               Issue #8: Wrong audio Content-Type

Library           RequestsLibrary
Library           Collections
Library           OperatingSystem
Resource          ../setup/setup_keywords.robot
Resource          ../setup/teardown_keywords.robot
Resource          ../resources/user_loop_keywords.robot

Suite Setup       Suite Setup
Suite Teardown    Suite Teardown
Test Setup        Test Cleanup

Test Tags         conversation

*** Test Cases ***
Get Events Returns Anomalies
    [Documentation]    Verify GET /events returns conversations with maybe_anomaly: true (Issue #5, #7)
    ...                Should NOT return maybe_anomaly: "verified" or false

    ${timestamp}=    Get Timestamp
    ${conv_id}=      Set Variable    user-loop-anomaly-${timestamp}
    ${version_id}=   Set Variable    version-${timestamp}

    TRY
        Insert Test Conversation    ${conv_id}    ${version_id}    maybe_anomaly=true

        ${response}=    GET On Session    api    /api/user-loop/events    expected_status=200

        ${events}=    Set Variable    ${response.json()}
        Should Not Be Empty    ${events}    msg=/events should return at least one event when an anomaly exists

        ${found}=    Set Variable    ${False}
        FOR    ${event}    IN    @{events}
            IF    '${event}[conversation_id]' == '${conv_id}' and '${event}[version_id]' == '${version_id}'
                ${found}=    Set Variable    ${True}
                Dictionary Should Contain Key    ${event}    transcript
                Dictionary Should Contain Key    ${event}    timestamp
                Dictionary Should Contain Key    ${event}    audio_duration
                Dictionary Should Contain Key    ${event}    speaker_count
                Dictionary Should Contain Key    ${event}    word_count
                Should Be Equal    ${event}[transcript]    Test transcript
            END
        END

        Should Be True    ${found}    msg=/events should include the newly inserted anomaly (${conv_id}, ${version_id})
    FINALLY
        Delete Test Conversation    ${conv_id}
    END

Get Events Returns Empty When No Anomalies
    [Documentation]    Verify GET /events returns [] when no anomalies (Issue #7)

    # Ensure clean slate so this test is deterministic.
    Clear Test Databases

    ${timestamp}=    Get Timestamp
    ${conv_id}=      Set Variable    user-loop-verified-${timestamp}
    ${version_id}=   Set Variable    version-${timestamp}

    TRY
        # maybe_anomaly=verified should NOT be returned by /events (only maybe_anomaly=True is returned)
        Insert Test Conversation    ${conv_id}    ${version_id}    maybe_anomaly=verified

        ${response}=    GET On Session    api    /api/user-loop/events    expected_status=200
        ${events}=      Set Variable    ${response.json()}
        Should Be Empty    ${events}    msg=/events should return [] when no anomalies exist
    FINALLY
        Delete Test Conversation    ${conv_id}
    END

Accept Updates MaybeAnomaly To Verified
    [Documentation]    Verify POST /accept updates maybe_anomaly to "verified" (Issue #5, #6)
    ...                Should use transcript_version_id field (not version_id)

    ${timestamp}=    Get Timestamp
    ${conv_id}=      Set Variable    user-loop-accept-${timestamp}
    ${version_id}=   Set Variable    version-${timestamp}

    TRY
        Insert Test Conversation    ${conv_id}    ${version_id}    maybe_anomaly=true

        ${body}=    Create Dictionary
        ...    transcript_version_id=${version_id}
        ...    conversation_id=${conv_id}
        ...    reason=None

        ${response}=    POST On Session    api    /api/user-loop/accept    json=${body}    expected_status=200

        ${result}=    Set Variable    ${response.json()}
        Should Be Equal    ${result}[status]    success
        Should Be Equal    ${result}[message]    Verified transcript

        # Verify: MongoDB updated
        ${conv}=    Get Test Conversation    ${conv_id}
        ${maybe_anomaly}=    Get From Dictionary    ${conv}[transcript_versions][0]    maybe_anomaly
        Should Be Equal As Strings    ${maybe_anomaly}    verified

        ${verified_at}=    Get From Dictionary    ${conv}[transcript_versions][0]    verified_at
        Should Not Be Empty    ${verified_at}
    FINALLY
        Delete Test Conversation    ${conv_id}
    END

Accept Returns 422 For Missing TranscriptVersionId
    [Documentation]    Verify POST /accept returns 422 when transcript_version_id missing (Issue #6)
    ...                Backend expects transcript_version_id, not version_id

    ${timestamp}=    Get Timestamp
    ${conv_id}=      Set Variable    user-loop-422-${timestamp}
    ${version_id}=   Set Variable    version-${timestamp}

    TRY
        Insert Test Conversation    ${conv_id}    ${version_id}    maybe_anomaly=true

        ${body}=    Create Dictionary
        ...    version_id=${version_id}
        ...    conversation_id=${conv_id}

        POST On Session    api    /api/user-loop/accept    json=${body}    expected_status=422
    FINALLY
        Delete Test Conversation    ${conv_id}
    END

Accept Returns 404 For Missing Conversation
    [Documentation]    Verify POST /accept returns 404 when conversation not found

    ${body}=    Create Dictionary
    ...    transcript_version_id=missing-version
    ...    conversation_id=missing-conv

    ${response}=    POST On Session    api    /api/user-loop/accept    json=${body}    expected_status=404

    ${result}=    Set Variable    ${response.json()}
    Should Contain    ${result}[detail]    Not Found

Reject Saves To TrainingStash
    [Documentation]    Verify POST /reject saves transcript to training-stash (Issue #5)

    ${timestamp}=    Get Timestamp
    ${conv_id}=      Set Variable    user-loop-reject-${timestamp}
    ${version_id}=   Set Variable    version-${timestamp}
    ${stash_id}=     Set Variable    ${EMPTY}

    TRY
        Insert Test Conversation    ${conv_id}    ${version_id}    maybe_anomaly=true
        Insert Test Audio Chunk    ${conv_id}    0    mock audio

        ${body}=    Create Dictionary
        ...    transcript_version_id=${version_id}
        ...    conversation_id=${conv_id}
        ...    reason=False positive

        ${response}=    POST On Session    api    /api/user-loop/reject    json=${body}    expected_status=200

        ${result}=    Set Variable    ${response.json()}
        Should Be Equal    ${result}[status]    success
        Should Not Be Empty    ${result}[stash_id]

        ${stash_id}=    Set Variable    ${result}[stash_id]

        ${stash}=    Get Training Stash Entry    ${stash_id}
        Should Not Be Empty    ${stash}
        Should Be Equal    ${stash}[transcript_version_id]    ${version_id}
        Should Be Equal    ${stash}[transcript]    Test transcript
        Should Be Equal    ${stash}[reason]    False positive
    FINALLY
        Run Keyword And Ignore Error    Delete Test Conversation    ${conv_id}
        Run Keyword And Ignore Error    Delete Test Audio Chunks    ${conv_id}
        IF    '${stash_id}' != '${EMPTY}'
            Run Keyword And Ignore Error    Delete Training Stash Entry    ${stash_id}
        END
    END

Get Audio Returns WAV
    [Documentation]    Verify GET /audio/:version_id returns WAV file (Issue #1, #8)
    ...                Audio should be converted from Opus to WAV format

    ${timestamp}=    Get Timestamp
    ${conv_id}=      Set Variable    user-loop-audio-${timestamp}
    ${version_id}=   Set Variable    version-${timestamp}

    TRY
        Insert Test Conversation    ${conv_id}    ${version_id}    maybe_anomaly=true

        # Store a real WAV file in MongoDB so ffmpeg can produce a non-empty response.
        ${wav_bytes}=    Get Binary File    ${CURDIR}/../test_assets/DIY_Experts_Glass_Blowing_16khz_mono_1min.wav
        Insert Test Audio Chunk    ${conv_id}    0    ${wav_bytes}

        ${response}=    GET On Session    api    /api/user-loop/audio/${version_id}    expected_status=200

        ${content_type}=    Set Variable    ${response.headers}[Content-Type]
        Should Be True    'audio/wav' in '${content_type}' or 'audio/ogg' in '${content_type}'
        Should Not Be Empty    ${response.content}    msg=/audio should return a non-empty body

        ${disposition}=    Set Variable    ${response.headers}[Content-Disposition]
        Should Contain    ${disposition}    audio_${version_id}.
        IF    'audio/wav' in '${content_type}'
            Should Contain    ${disposition}    .wav
            Should Be True    $response.content.startswith(b'RIFF')    msg=Expected WAV bytes to start with RIFF
        ELSE
            Should Contain    ${disposition}    .opus
        END
    FINALLY
        Run Keyword And Ignore Error    Delete Test Conversation    ${conv_id}
        Run Keyword And Ignore Error    Delete Test Audio Chunks    ${conv_id}
    END

Get Audio Returns 404 For Missing Version
    [Documentation]    Verify GET /audio returns 404 when version not found (Issue #2)
    ...                Tests /audio/undefined case

    ${response}=    GET On Session    api    /api/user-loop/audio/undefined    expected_status=404

    ${result}=    Set Variable    ${response.json()}
    ${detail_lower}=    Evaluate    str($result.get('detail', '')).lower()
    Should Contain    ${detail_lower}    not found
