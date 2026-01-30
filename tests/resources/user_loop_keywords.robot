*** Settings ***
Documentation     User-loop service keywords for Robot Framework tests

Library          ../libs/user_loop_helper.py    WITH NAME    UserLoopHelper

*** Keywords ***
Insert Test Conversation
    [Documentation]    Insert test conversation into MongoDB
    [Arguments]    ${conv_id}    ${version_id}    ${maybe_anomaly}

    ${result}=    UserLoopHelper.Insert Test Conversation    ${conv_id}    ${version_id}    ${maybe_anomaly}
    RETURN    ${result}

Delete Test Conversation
    [Documentation]    Delete test conversation from MongoDB
    [Arguments]    ${conv_id}

    ${result}=    UserLoopHelper.Delete Test Conversation    ${conv_id}
    RETURN    ${result}

Get Test Conversation
    [Documentation]    Get test conversation from MongoDB
    [Arguments]    ${conv_id}

    ${doc}=    UserLoopHelper.Get Test Conversation    ${conv_id}
    RETURN    ${doc}

Insert Test Audio Chunk
    [Documentation]    Insert test audio chunk into MongoDB
    [Arguments]    ${conv_id}    ${chunk_index}    ${audio_data}

    ${result}=    UserLoopHelper.Insert Test Audio Chunk    ${conv_id}    ${chunk_index}    ${audio_data}
    RETURN    ${result}

Delete Test Audio Chunks
    [Documentation]    Delete all test audio chunks for a conversation
    [Arguments]    ${conv_id}

    ${result}=    UserLoopHelper.Delete Test Audio Chunks    ${conv_id}
    RETURN    ${result}

Get Training Stash Entry
    [Documentation]    Get training stash entry from MongoDB
    [Arguments]    ${stash_id}

    ${doc}=    UserLoopHelper.Get Training Stash Entry    ${stash_id}
    RETURN    ${doc}

Delete Training Stash Entry
    [Documentation]    Delete training stash entry from MongoDB
    [Arguments]    ${stash_id}

    ${result}=    UserLoopHelper.Delete Training Stash Entry    ${stash_id}
    RETURN    ${result}

Get Timestamp
    [Documentation]    Get current timestamp
    [Arguments]    ${format}=epoch
    
    ${time}=    Evaluate    int(time.time())    time
    RETURN    ${time}
