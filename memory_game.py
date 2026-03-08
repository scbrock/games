import streamlit as st
import random

# Initialize session state
if 'cards' not in st.session_state:
    st.session_state.cards = list(range(1, 9)) * 2
    random.shuffle(st.session_state.cards)
    st.session_state.revealed = [False] * 16
    st.session_state.matched = [False] * 16
    st.session_state.first_card = None
    st.session_state.second_card = None
    st.session_state.score = 0
    st.session_state.moves = 0

st.title("Memory Game 🎮")
st.write(f"**Score:** {st.session_state.score} | **Moves:** {st.session_state.moves}")

# Display cards
cols = st.columns(4)
for i in range(16):
    with cols[i % 4]:
        if st.session_state.matched[i]:
            st.button("✓", disabled=True, key=f"card_{i}")
        elif st.session_state.revealed[i]:
            st.button(str(st.session_state.cards[i]), disabled=True, key=f"card_{i}")
        else:
            if st.button("?", key=f"card_{i}"):
                # Handle card click
                if st.session_state.first_card is None:
                    st.session_state.first_card = i
                    st.session_state.revealed[i] = True
                elif st.session_state.second_card is None and i != st.session_state.first_card:
                    st.session_state.second_card = i
                    st.session_state.revealed[i] = True
                    st.session_state.moves += 1
                    
                    # Check for match
                    if st.session_state.cards[st.session_state.first_card] == st.session_state.cards[st.session_state.second_card]:
                        st.session_state.matched[st.session_state.first_card] = True
                        st.session_state.matched[st.session_state.second_card] = True
                        st.session_state.score += 1
                        st.session_state.first_card = None
                        st.session_state.second_card = None
                    else:
                        st.rerun()

# Check if game is won
if all(st.session_state.matched):
    st.success(f"🎉 You won! Score: {st.session_state.score}, Moves: {st.session_state.moves}")

# Reset button
if st.button("Reset Game"):
    st.session_state.cards = list(range(1, 9)) * 2
    random.shuffle(st.session_state.cards)
    st.session_state.revealed = [False] * 16
    st.session_state.matched = [False] * 16
    st.session_state.first_card = None
    st.session_state.second_card = None
    st.session_state.score = 0
    st.session_state.moves = 0
    st.rerun()
