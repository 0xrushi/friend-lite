*** Settings ***
Documentation    Plugin Event System Integration Tests
...
...              Tests the event-driven plugin architecture by:
...              - Uploading audio and verifying transcript.batch events
...              - Streaming audio and verifying transcript.streaming events
...              - Verifying conversation.complete events after conversation ends
...              - Verifying memory.processed events after memory extraction
Library          RequestsLibrary
Library          Collections
Library          String
Library          OperatingSystem
Resource         ../setup/setup_keywords.robot
Resource         ../setup/teardown_keywords.robot
Resource         ../resources/user_keywords.robot
Resource         ../resources/conversation_keywords.robot
Resource         ../resources/audio_keywords.robot
Resource         ../resources/plugin_keywords.robot
Resource         ../resources/websocket_keywords.robot
Variables        ../setup/test_data.py
Suite Setup      Suite Setup
Suite Teardown   Suite Teardown

*** Variables ***
# TEST_AUDIO_FILE is loaded from test_data.py

*** Test Cases ***

Verify Test Plugin Configuration
    [Documentation]    Verify test plugin config file is properly formatted
    [Tags]    infra

    # Verify test config file exists
    File Should Exist    ${CURDIR}/../config/plugins.test.yml
    ...    msg=Test plugin config file should exist

    # Verify test_event plugin is configured
    ${config_content}=    Get File    ${CURDIR}/../config/plugins.test.yml
    Should Contain    ${config_content}    test_event
    ...    msg=Test config should contain test_event plugin

    Should Contain    ${config_content}    transcript.streaming
    ...    msg=Test plugin should subscribe to transcript.streaming

    Should Contain    ${config_content}    transcript.batch
    ...    msg=Test plugin should subscribe to transcript.batch

Upload Audio And Verify Transcript Batch Event
    [Documentation]    Upload audio file and verify transcript.batch event is dispatched
    [Tags]    audio-upload

    # Clear any existing events
    Clear Plugin Events

    # Get baseline event count
    ${baseline_count}=    Get Plugin Event Count    transcript.batch

    # Upload test audio file
    File Should Exist    ${TEST_AUDIO_FILE}
    ...    msg=Test audio file should exist
    ${result}=    Upload Audio For Processing    ${TEST_AUDIO_FILE}

    # Wait for transcription to complete
    Sleep    15s

    # Query plugin events database
    ${final_count}=    Get Plugin Event Count    transcript.batch
    ${new_events}=    Evaluate    ${final_count} - ${baseline_count}

    # Verify at least one new event was received
    Should Be True    ${new_events} > 0
    ...    msg=At least one transcript.batch event should be logged

    # Get the events and verify structure
    ${events}=    Get Plugin Events By Type    transcript.batch
    Should Not Be Empty    ${events}
    ...    msg=Should have transcript.batch events

    # Verify first event has required fields
    ${event}=    Set Variable    ${events}[0]
    Log    Event data: ${event}

    # Verify event contains transcript data (data field is JSON, so check the data column)
    Should Not Be Empty    ${event}[3]
    ...    msg=Event should have transcript data

Conversation Complete Should Trigger Event
    [Documentation]    Verify conversation.complete event after conversation ends
    [Tags]    conversation

    # Clear events
    Clear Plugin Events

    # Get baseline count
    ${baseline_count}=    Get Plugin Event Count    conversation.complete

    # Upload audio (triggers conversation creation and completion)
    File Should Exist    ${TEST_AUDIO_FILE}
    ${result}=    Upload Audio For Processing    ${TEST_AUDIO_FILE}

    # Wait for full pipeline: transcription → conversation
    Sleep    20s

    # Verify conversation.complete event
    ${final_count}=    Get Plugin Event Count    conversation.complete
    ${new_events}=    Evaluate    ${final_count} - ${baseline_count}

    Should Be True    ${new_events} > 0
    ...    msg=At least one conversation.complete event should be logged

    # Verify event structure
    ${events}=    Get Plugin Events By Type    conversation.complete
    Should Not Be Empty    ${events}

Memory Processing Should Trigger Event
    [Documentation]    Verify memory.processed event after memory extraction
    [Tags]    memory

    # Clear events
    Clear Plugin Events

    # Get baseline count
    ${baseline_count}=    Get Plugin Event Count    memory.processed

    # Upload audio with meaningful content for memory extraction
    File Should Exist    ${TEST_AUDIO_FILE}
    ${result}=    Upload Audio For Processing    ${TEST_AUDIO_FILE}

    # Wait for full pipeline: transcription → conversation → memory
    Sleep    30s

    # Verify memory.processed event
    ${final_count}=    Get Plugin Event Count    memory.processed
    ${new_events}=    Evaluate    ${final_count} - ${baseline_count}

    Should Be True    ${new_events} > 0
    ...    msg=At least one memory.processed event should be logged

    # Verify event structure
    ${events}=    Get Plugin Events By Type    memory.processed
    Should Not Be Empty    ${events}

Verify All Events Are Logged
    [Documentation]    Comprehensive test that verifies all event types are logged
    [Tags]    e2e

    # Clear all events
    Clear Plugin Events

    # Get baseline counts for all event types
    ${batch_baseline}=    Get Plugin Event Count    transcript.batch
    ${conv_baseline}=    Get Plugin Event Count    conversation.complete
    ${mem_baseline}=    Get Plugin Event Count    memory.processed

    # Upload audio file (should trigger all events)
    File Should Exist    ${TEST_AUDIO_FILE}
    ${result}=    Upload Audio For Processing    ${TEST_AUDIO_FILE}

    # Wait for full pipeline
    Sleep    35s

    # Verify all events were triggered
    ${batch_final}=    Get Plugin Event Count    transcript.batch
    ${conv_final}=    Get Plugin Event Count    conversation.complete
    ${mem_final}=    Get Plugin Event Count    memory.processed

    ${batch_new}=    Evaluate    ${batch_final} - ${batch_baseline}
    ${conv_new}=    Evaluate    ${conv_final} - ${conv_baseline}
    ${mem_new}=    Evaluate    ${mem_final} - ${mem_baseline}

    Should Be True    ${batch_new} > 0
    ...    msg=transcript.batch events should be logged

    Should Be True    ${conv_new} > 0
    ...    msg=conversation.complete events should be logged

    Should Be True    ${mem_new} > 0
    ...    msg=memory.processed events should be logged

    # Log summary
    Log    Events logged - Batch: ${batch_new}, Conversation: ${conv_new}, Memory: ${mem_new}

*** Keywords ***
Test Suite Setup
    [Documentation]    Setup for plugin event tests
    # Standard suite setup
    Suite Setup

    # Verify test audio file exists
    File Should Exist    ${TEST_AUDIO_FILE}
    ...    msg=Test audio file must exist for integration tests

Test Cleanup
    [Documentation]    Cleanup after each test
    # Standard cleanup
    # Note: We intentionally don't clear plugin events between tests
    # to allow for debugging and event inspection

Upload Audio For Processing
    [Arguments]    ${audio_file}
    [Documentation]    Upload audio file for batch processing

    # Get admin session
    ${session}=    Get Admin API Session

    # Upload audio file
    ${files}=    Create Dictionary    files=${audio_file}
    ${response}=    POST On Session    ${session}    /api/process-audio-files
    ...    files=${files}
    ...    expected_status=200

    ${result}=    Set Variable    ${response.json()}
    Log    Upload result: ${result}

    RETURN    ${result}
