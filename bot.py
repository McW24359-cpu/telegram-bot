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

user_data = {}
verified_users = set()

EMOJIS = ["🍎", "🐶", "🚗", "⭐", "⚽"]
TYPING_WORDS = ["READY", "HUMAN", "VERIFY", "START", "PASS", "CODE", "WELCOME"]


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

  if current_step == "math":
    try:
      user_val = int(message.text.strip())
      if user_val == state["math_ans"]:
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
        num1 = random.randint(1, 10)
        num2 = random.randint(1, 10)
        state["math_ans"] = num1 + num2
        await message.answer(
            "❌ Incorrect answer. Let's try a new"
            f" one:\n\nWhat is **{num1} + {num2}**?"
        )
    except ValueError:
      await message.answer("Please type a valid number.")

  elif current_step == "typing":
    expected_text = state.get("typing_text", "READY")

    if message.text.strip().upper() != expected_text.upper():
      user_data.pop(user_id, None)
      await message.answer(
          "❌ Incorrect text. Captcha failed! Type /start to try again."
      )
      return

    user_data.pop(user_id, None)
    verified_users.add(user_id)

    try:
      # Explicit check/generation of invite link
      invite = await bot.create_chat_invite_link(
          chat_id=GROUP_ID, creates_join_request=True
      )

      builder = InlineKeyboardBuilder()
      builder.button(text="✅ Send Join Request", url=invite.invite_link)

      await message.answer(
          "🎉 **Verification Complete!**\n\nClick the button below to send your"
          " join request to the group. The bot will automatically approve"
          " you within 5 seconds!",
          reply_markup=builder.as_markup(),
      )
    except Exception as e:
      logging.error(f"Failed to create invite link for {GROUP_ID}: {e}")
      await message.answer(
          f"Verification passed, but failed to create link. Error: {e}"
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
    random_word = random.choice(TYPING_WORDS)
    user_data[user_id]["step"] = "typing"
    user_data[user_id]["typing_text"] = random_word

    await callback.message.edit_text(
        "✅ Correct emoji selected!\n\n⌨️ **Step 3 of 3: Final Step**\nPlease type"
        f" the exact word **{random_word}** in chat to complete your"
        " verification."
    )
  else:
    user_data.pop(user_id, None)
    await callback.message.edit_text(
        "❌ Wrong emoji selected! Captcha failed. Send /start to try again."
    )


@dp.chat_join_request()
async def handle_join_request(event: types.ChatJoinRequest):
  user_id = event.from_user.id
  await asyncio.sleep(5)
  try:
    await bot.approve_chat_join_request(
        chat_id=event.chat.id, user_id=user_id
    )
    verified_users.discard(user_id)
  except Exception as e:
    logging.error(f"Failed to approve join request: {e}")


async def main():
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
