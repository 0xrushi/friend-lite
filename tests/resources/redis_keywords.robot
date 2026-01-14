*** Settings ***
Documentation    Redis session management and verification keywords
...
...              This file contains keywords for interacting with Redis sessions
...              and verifying session state during tests.
...
...              Keywords in this file handle:
...              - Reading Redis session data
...              - Verifying session schema
...              - Session state checks
...
...              Keywords that should NOT be in this file:
...              - Verification/assertion keywords (belong in tests)
...              - API session management (belong in session_resources.robot)
Library          Process
Library          Collections
Variables        ../setup/test_env.py

*** Keywords ***

Get Redis Session Data
    [Documentation]    Get session data from Redis for a given stream/session ID
    [Arguments]    ${session_id}

    # Use redis-cli to get session hash
    ${redis_key}=    Set Variable    audio:session:${session_id}
    ${result}=    Run Process    docker    exec    ${REDIS_CONTAINER}
    ...    redis-cli    HGETALL    ${redis_key}

    Should Be Equal As Integers    ${result.rc}    0
    ...    Redis command failed: ${result.stderr}

    # Parse output (HGETALL returns: field1 value1 field2 value2 ...)
    @{lines}=    Split String    ${result.stdout}    \n
    &{session_data}=    Create Dictionary

    # Process pairs
    ${length}=    Get Length    ${lines}
    FOR    ${i}    IN RANGE    0    ${length}    2
        ${key}=    Get From List    ${lines}    ${i}
        ${value_index}=    Evaluate    ${i} + 1
        IF    ${value_index} < ${length}
            ${value}=    Get From List    ${lines}    ${value_index}
            Set To Dictionary    ${session_data}    ${key}=${value}
        END
    END

    RETURN    ${session_data}


Verify Session Has Field
    [Documentation]    Verify a Redis session has a specific field
    [Arguments]    ${session_id}    ${field_name}

    ${session}=    Get Redis Session Data    ${session_id}
    Dictionary Should Contain Key    ${session}    ${field_name}
    ...    Session ${session_id} missing field: ${field_name}


Get Session Field Value
    [Documentation]    Get a specific field value from Redis session
    [Arguments]    ${session_id}    ${field_name}

    ${session}=    Get Redis Session Data    ${session_id}
    ${value}=    Get From Dictionary    ${session}    ${field_name}
    RETURN    ${value}


Session Field Should Equal
    [Documentation]    Verify a session field has a specific value
    [Arguments]    ${session_id}    ${field_name}    ${expected_value}

    ${actual}=    Get Session Field Value    ${session_id}    ${field_name}
    Should Be Equal    ${actual}    ${expected_value}
    ...    Session field ${field_name} mismatch: expected ${expected_value}, got ${actual}


Redis Command
    [Documentation]    Execute a generic Redis command and return the result
    ...                Useful for operations like XLEN, XRANGE, etc.
    [Arguments]    ${command}    @{args}

    # Execute redis-cli command
    ${result}=    Run Process    docker    exec    ${REDIS_CONTAINER}
    ...    redis-cli    ${command}    @{args}

    Should Be Equal As Integers    ${result.rc}    0
    ...    Redis command failed: ${result.stderr}

    # Return stdout, stripping whitespace
    ${output}=    Strip String    ${result.stdout}

    # Try to convert to integer if it's a number (for commands like XLEN)
    ${is_digit}=    Run Keyword And Return Status    Should Match Regexp    ${output}    ^\\d+$
    ${return_value}=    Run Keyword If    ${is_digit}
    ...    Convert To Integer    ${output}
    ...    ELSE    Set Variable    ${output}

    RETURN    ${return_value}


Get Backend Logs
    [Documentation]    Get backend container logs for debugging
    [Arguments]    ${since}=5m

    ${result}=    Run Process    docker    compose    logs    --since    ${since}    chronicle-backend
    ...    shell=True    stderr=STDOUT

    RETURN    ${result.stdout}
