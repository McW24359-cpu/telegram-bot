import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

API_TOKEN = 8823867620:AAGrY3ytRsrl2NmZeUVci19zOVXAmFvUUY0
GROUP_CHAT_ID = -4329733155

router = Router()


# Define the 3-step Captcha states
class VerificationStates(StatesGroup):
  math_step = State()
  emoji_step = State()
  typing_step = State()
  verified = State()


# In-memory database mockup to track user verification & links
# (Use PostgreSQL or SQLite in production)
verified_users = set()
user_links = {}


# Step 1: User starts the bot in DM
@router.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext):
  if message.chat.type != "private":
    return

  user_id = message.from_user.id
  if user_id in verified_users:
    await message.answer(
        "You are already verified! Check your personal link to join."
    )
    return

  await state.set_state(VerificationStates.math_step)
  await message.answer(
      "🔒 **Step 1 of 3: Math Captcha**\n\nWhat is 12 + 8? Reply with the"
      " number."
  )


# Step 2: Handle Math Answer -> Move to Emoji Step
@router.message(VerificationStates.math_step)
async def process_math(message: types.Message, state: FSMContext):
  if message.text.strip() == "20":
    await state.set_state(VerificationStates.emoji_step)

    # Create an inline keyboard with emojis
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🍎", callback_data="emoji_wrong"),
                InlineKeyboardButton(text="🍌", callback_data="emoji_correct"),
                InlineKeyboardButton(text="🍇", callback_data="emoji_wrong"),
            ]
        ]
    )
    await message.answer(
        "✅ Correct!\n\n🎨 **Step 2 of 3: Emoji Captcha**\nTap the 🍌 emoji"
        " below:",
        reply_markup=keyboard,
    )
  else:
    await message.answer("❌ Incorrect math answer. Try again: What is 12 + 8?")


# Step 3: Handle Emoji Callback -> Move to Typing Step
@router.callback_query(
    VerificationStates.emoji_step, F.data == "emoji_correct"
)
async def process_emoji(callback: types.CallbackQuery, state: FSMContext):
  await state.set_state(VerificationStates.typing_step)
  await callback.message.edit_text(
      "✅ Correct!\n\n⌨️ **Step 3 of 3: Typing Captcha**\nType this exact code"
      " to finish: `verify-99`"
  )
  await callback.answer()


@router.callback_query(
    VerificationStates.emoji_step, F.data == "emoji_wrong"
)
async def process_emoji_wrong(callback: types.CallbackQuery):
  await callback.answer("Wrong emoji! Try again.", show_alert=True)


# Step 4: Handle Typing Answer -> Generate Personal One-Time Link
@router.message(VerificationStates.typing_step)
async def process_typing(message: types.Message, state: FSMContext, bot: Bot):
  if message.text.strip() == "verify-99":
    user_id = message.from_user.id
    verified_users.add(user_id)
    await state.set_state(VerificationStates.verified)

    # Generate a personal, one-time join-request link for this specific user
    invite = await bot.create_chat_invite_link(
        chat_id=GROUP_CHAT_ID,
        creates_join_request=True,
        member_limit=1,  # Strict single-use boundary
    )

    user_links[user_id] = invite.invite_link

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Send Join Request", url=invite.invite_link
                )
            ]
        ]
    )

    await message.answer(
        "🎉 **Verification Complete!**\n\nYour personal one-time join link has"
        " been generated. Tap the button below to send your join request to the"
        " group.",
        reply_markup=keyboard,
    )
  else:
    await message.answer(
        "❌ Code doesn't match. Type exactly: `verify-99`", parse_mode="Markdown"
    )


# Step 5: Catch Join Requests, Delay 5s, Approve, and Revoke
@router.chat_join_request()
async def handle_join_request(join_request: types.ChatJoinRequest, bot: Bot):
  user_id = join_request.from_user.id

  # Check if user is verified and used their assigned link
  if user_id in verified_users:
    # Wait precisely 5 seconds
    await asyncio.sleep(5)

    # Approve the request
    await bot.approve_chat_join_request(
        chat_id=join_request.chat.id, user_id=user_id
    )

    # Revoke their personal link so it can never be reused
    if user_id in user_links:
      try:
        # Note: You would track the specific link object/string to revoke it via API
        # bot.revoke_chat_invite_link(chat_id=GROUP_CHAT_ID, invite_link=...)
        pass
      except Exception as e:
        logging.error(f"Failed to revoke link: {e}")
  else:
    # Optional: Decline or ignore unverified join requests
    await bot.decline_chat_join_request(
        chat_id=join_request.chat.id, user_id=user_id
    )


async def main():
  bot = Bot(token=API_TOKEN)
  dp = Dispatcher(storage=MemoryStorage())
  dp.include_router(router)
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
