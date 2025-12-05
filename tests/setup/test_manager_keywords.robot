*** Settings ***
Documentation    Test data management and fixture creation keywords
...
...              This file contains keywords for managing test data, clearing databases,
...              creating fixtures, and managing test state.
...
...              Keywords in this file handle:
...              - Database clearing operations
...              - Fixture conversation creation
...              - Test data reset
...              - Random ID generation for test data
...
...              Keywords that should NOT be in this file:
...              - Docker service management (belong in setup_env_keywords.robot)
...              - Health check endpoints (belong in health_keywords.robot)
...              - User/session management (belong in respective resource files)
Library          OperatingSystem
Library          Process
Library          String
Library          Collections
Library          DateTime
Library          RequestsLibrary
Variables        test_env.py
Resource         ../resources/audio_keywords.robot
Resource         ../resources/conversation_keywords.robot
Resource         ../resources/websocket_keywords.robot
Resource         ../resources/queue_keywords.robot
Resource         ../resources/session_keywords.robot


*** Keywords ***

Clear Test Databases
    [Documentation]    Quickly clear test databases and audio files without restarting containers
    ...                (preserves admin user and fixture conversations tagged with is_fixture=true)
    Log To Console    Clearing test databases and audio files...

    # Clear MongoDB collections but preserve admin user and fixtures
    Run Process    docker exec advanced-mongo-test-1 mongosh test_db --eval "db.users.deleteMany({'email': {\\$ne:'${ADMIN_EMAIL}'}})"    shell=True

    # Clear conversations and audio_chunks except those tagged as fixtures
    Run Process    docker exec advanced-mongo-test-1 mongosh test_db --eval "db.conversations.deleteMany({\\$or: [{'is_fixture': {\\$exists: false}}, {'is_fixture': false}]})"    shell=True
    Run Process    docker exec advanced-mongo-test-1 mongosh test_db --eval "db.audio_chunks.deleteMany({\\$or: [{'is_fixture': {\\$exists: false}}, {'is_fixture': false}]})"    shell=True

    # Count fixtures for logging
    ${result}=    Run Process    docker exec advanced-mongo-test-1 mongosh test_db --eval "db.conversations.countDocuments({'is_fixture': true})" --quiet    shell=True
    ${fixture_count}=    Strip String    ${result.stdout}

    IF    '${fixture_count}' != '0'
        Log To Console    MongoDB cleared (preserved admin user + ${fixture_count} fixture conversation(s))
    ELSE
        Log To Console    MongoDB cleared (preserved admin user only)
    END

    # Clear admin user's registered_clients dict to prevent client_id counter increments
    Run Process    docker exec advanced-mongo-test-1 mongosh test_db --eval "db.users.updateOne({'email':'${ADMIN_EMAIL}'}, {\\$set: {'registered_clients': {}}})"    shell=True

    # Clear memory provider data (Qdrant or Mycelia)
    Clear Memory Provider Data

    # Clear audio files (except fixtures subfolder)
    Run Process    bash    -c    find ${EXECDIR}/backends/advanced/data/test_audio_chunks -maxdepth 1 -name "*.wav" -delete || true    shell=True
    Run Process    bash    -c    rm -rf ${EXECDIR}/backends/advanced/data/test_debug_dir/* || true    shell=True
    Log To Console    Audio files cleared (fixtures/ subfolder preserved)

    # Clear container audio files (except fixtures subfolder)
    Run Process    bash    -c    docker exec advanced-friend-backend-test-1 find /app/audio_chunks -maxdepth 1 -name "*.wav" -delete || true    shell=True
    Run Process    bash    -c    docker exec advanced-friend-backend-test-1 find /app/debug_dir -name "*" -type f -delete || true    shell=True

    # Clear Redis queues and job registries (preserve worker registrations, failed and completed jobs)
    # Delete all rq:* keys except worker registrations (rq:worker:*), failed jobs (rq:failed:*), and completed jobs (rq:finished:*)
    ${redis_clear_script}=    Set Variable    redis-cli --scan --pattern "rq:*" | grep -Ev "^rq:(worker|failed|finished)" | xargs -r redis-cli DEL; redis-cli --scan --pattern "audio:*" | xargs -r redis-cli DEL; redis-cli --scan --pattern "consumer:*" | xargs -r redis-cli DEL
    Run Process    docker    exec    advanced-redis-test-1    sh    -c    ${redis_clear_script}    shell=True
    Log To Console    Redis queues and job registries cleared (worker registrations preserved)

Clear All Test Data
    [Documentation]    Complete data wipe including admin user and fixtures (use with caution)
    Log To Console    Clearing ALL test data including admin user and fixtures...

    # Wipe all MongoDB collections
    Run Process    docker exec advanced-mongo-test-1 mongosh test_db --eval "db.users.deleteMany({})"    shell=True
    Run Process    docker exec advanced-mongo-test-1 mongosh test_db --eval "db.conversations.deleteMany({})"    shell=True
    Run Process    docker exec advanced-mongo-test-1 mongosh test_db --eval "db.audio_chunks.deleteMany({})"    shell=True
    Log To Console    MongoDB completely cleared

    # Clear Qdrant
    Run Process    curl    -s    -X    DELETE    http://localhost:6337/collections/memories    shell=True
    Run Process    curl    -s    -X    DELETE    http://localhost:6337/collections/conversations    shell=True

    # Clear all audio files
    Run Process    bash    -c    rm -rf ${EXECDIR}/backends/advanced/data/test_audio_chunks/* || true    shell=True
    Run Process    bash    -c    rm -rf ${EXECDIR}/backends/advanced/data/test_debug_dir/* || true    shell=True

    # Clear all Redis data
    Run Process    docker    exec    advanced-redis-test-1    redis-cli    FLUSHALL    shell=True
    Log To Console    All test data cleared



Reset Data Without Restart
    [Documentation]    Ultra-fast reset for rapid iteration (alias for Clear Test Databases)
    Clear Test Databases

Create Fixture Conversation
    [Documentation]    Create a persistent fixture conversation for reuse across tests
    ...                This conversation will NOT be deleted between test suites
    ...                Tags the conversation with is_fixture=true in MongoDB
    ...                Audio files will be stored in fixtures/ subfolder
    ...                Returns the conversation ID
    [Arguments]    ${device_name}=fixture-device

    Log To Console    \nCreating fixture conversation...

    # Upload test audio to fixtures folder
    ${conversation}=    Upload Audio File    ${TEST_AUDIO_FILE}    ${device_name}    folder=fixtures

    # Verify conversation was created successfully (MongoDB uses conversation_id as the field name)
    Dictionary Should Contain Key    ${conversation}    conversation_id
    ${conversation_id}=    Set Variable    ${conversation}[conversation_id]

    # Verify it has transcript content
    Dictionary Should Contain Key    ${conversation}    transcript
    ${transcript}=    Set Variable    ${conversation}[transcript]
    Should Not Be Empty    ${transcript}    Fixture conversation has no transcript

    # Tag this conversation as a fixture in MongoDB so cleanup preserves it
    ${result}=    Run Process    docker exec advanced-mongo-test-1 mongosh test_db --eval "db.conversations.updateOne({'conversation_id': '${conversation_id}'}, {\\$set: {'is_fixture': true}})"    shell=True
    Should Be Equal As Integers    ${result.rc}    0    Failed to tag conversation as fixture: ${result.stderr}

    # Also tag audio_chunks
    ${result2}=    Run Process    docker exec advanced-mongo-test-1 mongosh test_db --eval "db.audio_chunks.updateMany({'conversation_id': '${conversation_id}'}, {\\$set: {'is_fixture': true}})"    shell=True
    Should Be Equal As Integers    ${result2.rc}    0    Failed to tag audio chunks as fixture: ${result2.stderr}

    Log To Console    ✓ Audio files stored in fixtures/ subfolder

    ${transcript_len}=    Get Length    ${transcript}
    Log To Console    ✓ Fixture conversation created: ${conversation_id}
    Log To Console    ✓ Transcript length: ${transcript_len} chars
    Log To Console    ✓ Tagged as fixture (is_fixture=true)

    Set Global Variable    ${FIXTURE_CONVERSATION_ID}    ${conversation_id}

    RETURN    ${conversation_id}

Get Fixture Conversation
    [Documentation]    Get the persistent fixture conversation
    ...                Use this in tests that need an existing conversation without creating one
    ...                Returns the full conversation object

    # Check if fixture was created (uses Get Variable Value to avoid errors if not set)
    ${fixture_id}=    Get Variable Value    ${FIXTURE_CONVERSATION_ID}    ${EMPTY}

    IF    '${fixture_id}' == '${EMPTY}'
        Fail    Fixture conversation not created. Call 'Create Fixture Conversation' in suite setup first.
    END

    ${conversation}=    Get Conversation By ID    ${fixture_id}

    RETURN    ${conversation}

Log Test Phase
    [Documentation]    Log the current test phase with timing
    [Arguments]    ${phase_name}

    ${timestamp}=    Get Current Date    result_format=%Y-%m-%d %H:%M:%S
    Log    === PHASE: ${phase_name} (${timestamp}) ===    INFO

Test Cleanup
    [Documentation]    Standard test teardown - flush in-progress jobs and cleanup streams
    ...                Use this as Test Teardown for all tests
    # Try to cleanup audio streams if the keyword exists (websocket tests)
    Run Keyword And Ignore Error    Cleanup All Audio Streams
    Flush In Progress Jobs

Clear Memory Provider Data
    [Documentation]    Clear memory data based on the current memory provider
    ...                Automatically detects provider and clears appropriately:
    ...                - friend_lite: Clears Qdrant collections
    ...                - mycelia: Deletes all memories via Mycelia API

    # Check current provider from health endpoint
    TRY
        Create Session    provider_check_session    ${API_URL}    verify=False
        ${response}=    GET On Session    provider_check_session    /health
        ${health_data}=    Set Variable    ${response.json()}
        ${memory_service}=    Get From Dictionary    ${health_data}[services]    memory_service
        ${provider}=    Set Variable    ${memory_service}[provider]
        Delete All Sessions

        IF    '${provider}' == 'mycelia'
            Log To Console    Clearing Mycelia memories...
            Clear Mycelia Memories
        ELSE IF    '${provider}' == 'friend_lite'
            Log To Console    Clearing Qdrant collections...
            Clear Qdrant Collections
        ELSE
            Log To Console    Unknown provider '${provider}', attempting to clear both Qdrant and Mycelia...
            Clear Qdrant Collections
            Run Keyword And Ignore Error    Clear Mycelia Memories
        END
    EXCEPT
        Log To Console    Could not determine memory provider, clearing Qdrant as fallback
        Clear Qdrant Collections
    END

Clear Qdrant Collections
    [Documentation]    Clear Qdrant vector collections
    Run Process    curl    -s    -X    DELETE    http://localhost:6337/collections/memories    shell=True
    Run Process    curl    -s    -X    DELETE    http://localhost:6337/collections/conversations    shell=True
    Log To Console    ✓ Qdrant collections cleared

Clear Mycelia Memories
    [Documentation]    Clear all Mycelia memories for the admin user via backend API
    ...                Uses the backend's delete endpoint which calls Mycelia's delete_all_user_memories

    # Create admin session for API calls
    Create API Session    mycelia_cleanup_session

    # Get admin user ID
    ${response}=    GET On Session    mycelia_cleanup_session    /api/users/me
    Should Be Equal As Integers    ${response.status_code}    200
    ${user_data}=    Set Variable    ${response.json()}
    ${user_id}=    Set Variable    ${user_data}[id]

    # Get all memories to delete
    ${memories_response}=    GET On Session    mycelia_cleanup_session    /api/memories?limit=1000
    Should Be Equal As Integers    ${memories_response.status_code}    200
    ${memories_data}=    Set Variable    ${memories_response.json()}
    ${memories}=    Set Variable    ${memories_data}[memories]
    ${memory_count}=    Get Length    ${memories}

    # Delete each memory
    ${deleted_count}=    Set Variable    0
    FOR    ${memory}    IN    @{memories}
        ${memory_id}=    Set Variable    ${memory}[id]
        ${delete_response}=    DELETE On Session    mycelia_cleanup_session    /api/memories/${memory_id}    expected_status=any
        IF    ${delete_response.status_code} == 200
            ${deleted_count}=    Evaluate    ${deleted_count} + 1
        END
    END

    Delete All Sessions
    Log To Console    ✓ Cleared ${deleted_count} Mycelia memories for admin user
