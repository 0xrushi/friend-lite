*** Settings ***
Documentation    Test Creating Memory About Getting Married
...
...              This test creates a memory about getting married in a week
...              by sending a message to a chat session and extracting memories.

Library          RequestsLibrary
Library          Collections
Resource         ../setup/setup_keywords.robot
Resource         ../setup/teardown_keywords.robot
Resource         ../resources/memory_keywords.robot
Suite Setup      Suite Setup
Suite Teardown   Suite Teardown


*** Test Cases ***
Create Wedding Memory Via Add Memory Endpoint
    [Documentation]    Create a memory about getting married using POST /api/memories endpoint
    [Tags]    memory

    # Get initial memory count
    ${initial_memories}=    Get User Memories    api
    ${initial_count}=    Get Length    ${initial_memories}
    Log    Initial memory count: ${initial_count}

    # Create memory directly with wedding content
    ${wedding_content}=    Set Variable    I'm getting married in one week! It's going to be at the botanical gardens with about 150 guests. We've been planning this for over a year and I'm so excited but also nervous. The ceremony is next Saturday at 4pm followed by a reception.

    # Prepare request body as dictionary
    &{request_body}=    Create Dictionary    content=${wedding_content}    source_id=wedding_test

    # Add memory via POST /api/memories
    ${add_response}=    POST On Session    api    /api/memories    json=${request_body}
    Should Be Equal As Integers    ${add_response.status_code}    200
    ${add_data}=    Set Variable    ${add_response.json()}
    Log    Memory creation response: ${add_data}

    # Verify memory creation was successful
    Should Be True    ${add_data}[success]    Memory creation should succeed
    Should Be True    ${add_data}[count] > 0    Should create at least one memory
    Log    Created ${add_data}[count] memory/memories with IDs: ${add_data}[memory_ids]

    # Wait a moment for memory to be fully stored
    Sleep    2s

    # Get memories after extraction
    ${final_memories}=    Get User Memories    api
    ${final_count}=    Get Length    ${final_memories}
    Log    Final memory count: ${final_count}

    # Verify new memories were created
    Should Be True    ${final_count} > ${initial_count}    New memories should be created
    ${new_memory_count}=    Evaluate    ${final_count} - ${initial_count}
    Log    Created ${new_memory_count} new memory/memories

    # Search for the wedding memory
    ${search_results}=    Search Memories    api    wedding 
    Log    Search results: ${search_results}

    # Verify search found the wedding memory
    Should Be True    len(${search_results}) > 0    Should find wedding-related memory
    ${first_result}=    Set Variable    ${search_results}[0]
    ${memory_content}=    Convert To Lower Case    ${first_result}[memory]

    # Verify memory contains wedding-related information
    Should Contain Any    ${memory_content}    wedding    married    marry
    ...    Memory should contain wedding-related keywords
    Log    Found wedding memory: ${first_result}[memory]

    # Verify specific details are captured
    ${should_contain_week}=    Evaluate    "week" in """${memory_content}"""
    ${should_contain_botanical}=    Evaluate    "botanical" in """${memory_content}""" or "garden" in """${memory_content}"""
    ${should_contain_saturday}=    Evaluate    "saturday" in """${memory_content}"""

    Log    Memory contains 'week': ${should_contain_week}
    Log    Memory contains 'botanical/garden': ${should_contain_botanical}
    Log    Memory contains 'saturday': ${should_contain_saturday}

Verify Memory Persists In Mycelia
    [Documentation]    Verify the wedding memory is stored in Mycelia and can be retrieved
    [Tags]    memory

    # Search for wedding memory
    ${results}=    Search Memories    api    getting married
    Should Be True    len(${results}) > 0    Wedding memory should be searchable

    ${wedding_memory}=    Set Variable    ${results}[0]
    Should Not Be Empty    ${wedding_memory}[id]    Memory should have ID
    Should Not Be Empty    ${wedding_memory}[memory]    Memory should have content

    Log    Wedding memory ID: ${wedding_memory}[id]
    Log    Wedding memory content: ${wedding_memory}[memory]
