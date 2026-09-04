import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

API_TOKEN = "8823867620:AAGrY3ytRsrl2NmZeUVci19zOVXAmFvUUY0"
GROUP_ID = -4329733155

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Track user states and verification progress
# user_data = { user_id: {"step": "math", "math_ans": 12, "emoji_target": "🍎"} }
user_data = {}
verified_users = set()

EMOJIS = ["🍎", "🐶", "🚗", "⭐", "⚽"]


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
  if message.chat.type != "private":
    return

  user_id = message.from_user.id
  if user_id in verified_users:
    await message.answer(
        "You are already verified! Check your group invite link or request to"
        " join."
    )
    return

  # Generate random math question (e.g., 3 + 7 or 5 * 2)
  num1 = random.randint(1, 10)
  num2 = random.randint(1, 10)
  correct_ans = num1 + num2

  user_data[user_id] = {"step": "math", "math_ans": correct_ans}

  await message.answer(
      "🔒 **Step 1 of 3: Captcha Verification**\n\nTo prove you're human, please"
      f" solve this math problem:\nWhat is **{num1} + {num2}**?\n\n*(Type your"
      " answer as a number)*"
  )


@dp.message(F.text)
async def handle_text(message: types.Message):
  if message.chat.type != "private":
    return

  user_id = message.from_user.id
  if user_id not in user_data:
    await message.answer("Please send /start to begin verification.")
    return

  state = user_data[user_id]
  current_step = state.get("step")

  # Step 1: Math Verification Handler
  if current_step == "math":
    try:
      user_val = int(message.text.strip())
      if user_val == state["math_ans"]:
        # Move to Step 2: Emoji selection
        target_emoji = random.choice(EMOJIS)
        state["step"] = "emoji"
        state["emoji_target"] = target_emoji

        builder = InlineKeyboardBuilder()
        shuffled_emojis = EMOJIS.copy()
        random.shuffle(shuffled_emojis)
        for emoji in shuffled_emojis:
          builder.button(text=emoji, callback_data=f"emoji_{emoji}")
        builder.adjust(3)

        await message.answer(
            "✅ Correct!\n\n🧩 **Step 2 of 3: Emoji Captcha**\nTap the button"
            f" matching this emoji: **{target_emoji}**",
            reply_markup=builder.as_markup(),
        )
      else:
        # Incorrect math: Generate a NEW different question so they don't get stuck on the same numbers
        num1 = random.randint(1, 10)
        num2 = random.randint(1, 10)
        state["math_ans"] = num1 + num2
        await message.answer(
            "❌ Incorrect answer. Let's try a new"
            f" one:\n\nWhat is **{num1} + {num2}**?"
        )
    except ValueError:
      await message.answer("Please type a valid number.")

  # Step 3: Typing Verification Handler
  elif current_step == "typing":
    expected_text = state.get("typing_text", "VERIFY")
    if message.text.strip().upper() == expected_text:
      user_data.pop(user_id, None)
      verified_users.add(user_id)

      # Generate personal single-use join request link
      try:
        invite = await bot.create_chat_invite_link(
            chat_id=GROUP_ID, creates_join_request=True
        )

        builder = InlineKeyboardBuilder()
        builder.button(
            text="✅ Send Join Request", url=invite.invite_link
        )

        await message.answer(
            "🎉 **Verification Complete!**\n\nClick the button below to send your"
            " join request to the group. The bot will automatically approve"
            " you within 5 seconds!",
            reply_markup=builder.as_markup(),
        )
      except Exception as e:
        logging.error(f"Failed to create invite link: {e}")
        await message.answer(
            "Verification passed, but failed to generate link. Contact an"
            " admin."
        )
    else:
      await message.answer(
          f"❌ Incorrect text. Please type exactly: **{expected_text}**"
      )


@dp.callback_query(F.data.startswith("emoji_"))
async def handle_emoji_callback(callback: types.CallbackQuery):
  user_id = callback.from_user.id
  if user_id not in user_data or user_data[user_id].get("step") != "emoji":
    await callback.answer("Session expired or invalid. Type /start.")
    return

  chosen_emoji = callback.data.split("_")[1]
  target_emoji = user_data[user_id]["emoji_target"]

  if chosen_emoji == target_emoji:
    # Move to Step 3: Typing confirmation
    user_data[user_id]["step"] = "typing"
    user_data[user_id]["typing_text"] = "READY"

    await callback.message.edit_text(
        "✅ Correct emoji selected!\n\n⌨️ **Step 3 of 3: Final Step**\nPlease type"
        " the word **READY** in chat to complete your verification."
    )
  else:
    await callback.answer("Wrong emoji! Try again.", show_alert=True)


@dp.chat_join_request()
async def handle_join_request(event: types.ChatJoinRequest):
  user_id = event.from_user.id
  if user_id in verified_users:
    # 5-second delay before auto-approving
    await asyncio.sleep(5)
    try:
      await bot.approve_chat_join_request(
          chat_id=event.chat.id, user_id=user_id
      )
      verified_users.discard(user_id)  # Clean up after approval
    except Exception as e:
      logging.error(f"Failed to approve join request: {e}")


async def main():
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
