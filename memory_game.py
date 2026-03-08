import streamlit as st
import random
import time

# Initialize session state
if 'cards' not in st.session_state:
    st.session_state.cards = list(range(1, 9)) * 2
    random.shuffle(st.session_state.cards)
    st.session_state.matched = [False] * 16
    st.session_state.first_card = None
    st.session_state.second_card = None
    st.session_state.score = 0
    st.session_state.moves = 0
    st.session_state.show_mismatch = False

# Handle mismatch from previous turn — reset before rendering
if st.session_state.show_mismatch:
    st.session_state.show_mismatch = False
    st.session_state.first_card = None
    st.session_state.second_card = None

st.title("Memory Game 🎮")
st.write(f"**Score:** {st.session_state.score} | **Moves:** {st.session_state.moves}")

# Card emoji mapping for visual flair
card_emojis = {1: "🍎", 2: "🍊", 3: "🍋", 4: "🍇", 5: "🫐", 6: "🍉", 7: "🍒", 8: "🥝"}

def click_card(i):
    if st.session_state.matched[i]:
        return
    if st.session_state.first_card is None:
        st.session_state.first_card = i
    elif st.session_state.second_card is None and i != st.session_state.first_card:
        st.session_state.second_card = i
        st.session_state.moves += 1
        # Check match
        if st.session_state.cards[st.session_state.first_card] == st.session_state.cards[st.session_state.second_card]:
            st.session_state.matched[st.session_state.first_card] = True
            st.session_state.matched[st.session_state.second_card] = True
            st.session_state.score += 1
            st.session_state.first_card = None
            st.session_state.second_card = None
        else:
            # Flag mismatch — cards stay visible this render, reset next render
            st.session_state.show_mismatch = True

# Display cards in a 4x4 grid
for row in range(4):
    cols = st.columns(4)
    for col in range(4):
        i = row * 4 + col
        with cols[col]:
            if st.session_state.matched[i]:
                st.button(card_emojis[st.session_state.cards[i]], disabled=True, key=f"card_{i}")
            elif i == st.session_state.first_card or i == st.session_state.second_card:
                st.button(card_emojis[st.session_state.cards[i]], disabled=True, key=f"card_{i}")
            else:
                st.button("❓", key=f"card_{i}", on_click=click_card, args=(i,))

# Check if game is won
if all(st.session_state.matched):
    st.balloons()
    st.success(f"🎉 You won in {st.session_state.moves} moves!")

# Reset button
def reset_game():
    st.session_state.cards = list(range(1, 9)) * 2
    random.shuffle(st.session_state.cards)
    st.session_state.matched = [False] * 16
    st.session_state.first_card = None
    st.session_state.second_card = None
    st.session_state.score = 0
    st.session_state.moves = 0
    st.session_state.show_mismatch = False

st.button("🔄 Reset Game", on_click=reset_game)
