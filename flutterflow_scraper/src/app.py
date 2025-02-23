import streamlit as st
import asyncio
from agent import FlutterFlowAgent

# Initialize the agent
@st.cache_resource
def get_agent():
    return FlutterFlowAgent()

# Create the Streamlit UI
st.title("FlutterFlow Documentation Assistant")
st.write("Ask any question about FlutterFlow and I'll help you find the answer!")

# Initialize session state for chat history if it doesn't exist
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Create the question input
question = st.text_input("Your question:", key="question_input")

# Clear chat button
if st.button("Clear Chat"):
    st.session_state.chat_history = []
    get_agent().clear_memory()
    st.rerun()

# Handle question submission
if question:
    with st.spinner("Thinking..."):
        # Get the agent
        agent = get_agent()
        
        # Run the query
        response = asyncio.run(agent.query(question))
        
        # Add to chat history
        st.session_state.chat_history.append({
            "question": question,
            "response": response
        })

# Custom CSS for chat messages
st.markdown("""
<style>
.user-message {
    padding: 10px;
    border-radius: 15px;
    background-color: #2b5876;
    color: white;
    margin: 5px 0;
    font-weight: 500;
}
.assistant-message {
    padding: 10px;
    border-radius: 15px;
    background-color: #f8f9fa;
    color: #1e1e1e;
    margin: 5px 0;
    border: 1px solid #e0e0e0;
    font-weight: 500;
}
</style>
""", unsafe_allow_html=True)

# Display chat history (newest first)
for chat in reversed(st.session_state.chat_history):
    # User message
    st.markdown(f"""
        <div class="user-message">
            👤 {chat["question"]}
        </div>
    """, unsafe_allow_html=True)
    
    # Assistant message
    st.markdown(f"""
        <div class="assistant-message">
            🤖 {chat["response"]["answer"]}
        </div>
    """, unsafe_allow_html=True)
    
    st.write("---")
