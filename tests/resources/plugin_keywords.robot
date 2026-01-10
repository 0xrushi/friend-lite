*** Settings ***
Documentation    Plugin testing resource file
...
...              This file contains keywords for plugin testing.
...              Keywords in this file should handle:
...              - Mock plugin creation and registration
...              - Plugin event subscription verification
...              - Event dispatch testing
...              - Wake word trigger testing
...
Library          Collections
Library          OperatingSystem
Library          Process
Library          DatabaseLibrary

*** Keywords ***
Create Mock Plugin Config
    [Documentation]    Create a mock plugin configuration for testing
    [Arguments]    ${subscriptions}    ${trigger_type}=always    ${wake_words}=${NONE}

    ${config}=    Create Dictionary
    ...    enabled=True
    ...    subscriptions=${subscriptions}

    ${trigger}=    Create Dictionary    type=${trigger_type}
    IF    $wake_words is not None
        Set To Dictionary    ${trigger}    wake_words=${wake_words}
    END
    Set To Dictionary    ${config}    trigger=${trigger}

    RETURN    ${config}

Verify Plugin Config Format
    [Documentation]    Verify plugin config follows new event-based format
    [Arguments]    ${config}

    Dictionary Should Contain Key    ${config}    subscriptions
    ...    msg=Plugin config should have 'subscriptions' field

    ${subscriptions}=    Get From Dictionary    ${config}    subscriptions
    Should Be True    isinstance(${subscriptions}, list)
    ...    msg=Subscriptions should be a list

    ${length}=    Get Length    ${subscriptions}
    Should Be True    ${length} > 0
    ...    msg=Plugin should subscribe to at least one event

Verify Event Name Format
    [Documentation]    Verify event name follows hierarchical naming convention
    [Arguments]    ${event}

    Should Contain    ${event}    .
    ...    msg=Event name should contain dot separator (e.g., 'transcript.streaming')

    ${parts}=    Split String    ${event}    .
    ${length}=    Get Length    ${parts}
    Should Be True    ${length} > 1
    ...    msg=Event should have domain and type (e.g., 'transcript.streaming')

Verify Event Matches Subscription
    [Documentation]    Verify an event would match a subscription
    [Arguments]    ${event}    ${subscription}

    Should Be Equal    ${event}    ${subscription}
    ...    msg=Event '${event}' should match subscription '${subscription}'

Get Test Plugins Config Path
    [Documentation]    Get path to test plugins configuration
    RETURN    ${CURDIR}/../../config/plugins.yml

Verify HA Plugin Uses Events
    [Documentation]    Verify HomeAssistant plugin config uses event subscriptions

    ${plugins_yml}=    Get Test Plugins Config Path
    ${config_content}=    Get File    ${plugins_yml}

    Should Contain    ${config_content}    subscriptions:
    ...    msg=Plugin config should use 'subscriptions' field

    Should Contain    ${config_content}    transcript.streaming
    ...    msg=HA plugin should subscribe to 'transcript.streaming' event

    Should Not Contain    ${config_content}    access_level:
    ...    msg=Plugin config should NOT use old 'access_level' field

# Test Plugin Event Database Keywords

Clear Plugin Events
    [Documentation]    Clear all events from test plugin database
    Connect To Database    sqlite3    ${CURDIR}/../../backends/advanced/data/test_debug_dir/test_plugin_events.db
    Execute SQL String    DELETE FROM plugin_events
    Disconnect From Database

Get Plugin Events By Type
    [Arguments]    ${event_type}
    [Documentation]    Query plugin events by event type
    Connect To Database    sqlite3    ${CURDIR}/../../backends/advanced/data/test_debug_dir/test_plugin_events.db
    ${query}=    Query    SELECT * FROM plugin_events WHERE event = '${event_type}' ORDER BY created_at DESC
    Disconnect From Database
    RETURN    ${query}

Get Plugin Events By User
    [Arguments]    ${user_id}
    [Documentation]    Query plugin events by user_id
    Connect To Database    sqlite3    ${CURDIR}/../../backends/advanced/data/test_debug_dir/test_plugin_events.db
    ${query}=    Query    SELECT * FROM plugin_events WHERE user_id = '${user_id}' ORDER BY created_at DESC
    Disconnect From Database
    RETURN    ${query}

Get All Plugin Events
    [Documentation]    Get all events from test plugin database
    Connect To Database    sqlite3    ${CURDIR}/../../backends/advanced/data/test_debug_dir/test_plugin_events.db
    ${query}=    Query    SELECT * FROM plugin_events ORDER BY created_at DESC
    Disconnect From Database
    RETURN    ${query}

Get Plugin Event Count
    [Arguments]    ${event_type}=${NONE}
    [Documentation]    Get count of events, optionally filtered by type
    Connect To Database    sqlite3    ${CURDIR}/../../backends/advanced/data/test_debug_dir/test_plugin_events.db
    IF    '${event_type}' != 'None'
        ${count}=    Row Count    SELECT COUNT(*) FROM plugin_events WHERE event = '${event_type}'
    ELSE
        ${count}=    Row Count    SELECT COUNT(*) FROM plugin_events
    END
    Disconnect From Database
    RETURN    ${count}

Verify Event Contains Data
    [Arguments]    ${event}    @{required_fields}
    [Documentation]    Verify event contains required data fields
    FOR    ${field}    IN    @{required_fields}
        Dictionary Should Contain Key    ${event}    ${field}
        ...    msg=Event should contain field '${field}'
    END
