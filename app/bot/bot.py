"""Telegram bot Application setup — webhook mode, no polling."""

from __future__ import annotations

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from prisma.enums import UserRole
from app.config.settings import settings
from app.auth.service import SessionAuthenticationService
from app.auth.exceptions import UserNotApproved, InsufficientPermissions
from app.emr_client.exceptions import EMRLoginError

# Conversation states
ASK_EMR_USERNAME, ASK_EMR_PASSWORD = range(2)


def build_application(auth_service: SessionAuthenticationService) -> Application:
    """Construct the Telegram Application with all handlers registered."""

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        assert update.effective_user is not None
        assert update.message is not None
        assert context.user_data is not None
        tg_user = update.effective_user

        await update.message.reply_text("Welcome. Checking authorization...")

        try:
            session = await auth_service.authenticate(
                telegram_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
            )
        except UserNotApproved:
            await update.message.reply_text(
                "Your account is registered but not yet approved. "
                "Please contact an administrator."
            )
            return ConversationHandler.END

        context.user_data["user_id"] = session.user.id

        if not session.requires_login:
            await update.message.reply_text("Approved. You're already logged in to Apex.")
            return ConversationHandler.END

        await update.message.reply_text("Approved.")

        if session.user.emrUsername is None:
            await update.message.reply_text("Please enter your EMR username.")
            return ASK_EMR_USERNAME

        context.user_data["emr_username"] = session.user.emrUsername
        await update.message.reply_text("Please enter your EMR password.")
        return ASK_EMR_PASSWORD

    async def receive_emr_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        assert update.message is not None and update.message.text is not None
        assert context.user_data is not None

        context.user_data["emr_username"] = update.message.text.strip()
        await update.message.reply_text("Please enter your EMR password.")
        return ASK_EMR_PASSWORD

    async def receive_emr_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        assert update.message is not None and update.message.text is not None
        assert update.effective_chat is not None
        assert context.user_data is not None

        emr_password = update.message.text.strip()
        emr_username = context.user_data.get("emr_username")
        user_id = context.user_data.get("user_id")

        if emr_username is None or user_id is None:
            await update.effective_chat.send_message(
                "Something went wrong — please start over with /start."
            )
            return ConversationHandler.END

        try:
            await update.message.delete()
        except Exception:
            pass

        await update.effective_chat.send_message("Logging into Apex...")

        try:
            existing_user = await auth_service.users.get_by_id(user_id)
            if existing_user is None:
                await update.effective_chat.send_message(
                    "Something went wrong — please start over with /start."
                )
                return ConversationHandler.END

            await auth_service.login_to_emr(existing_user, emr_username, emr_password)
        except EMRLoginError:
            await update.effective_chat.send_message(
                "Login failed. Please check your EMR credentials and try /start again."
            )
            return ConversationHandler.END
        finally:
            emr_password = ""

        await update.effective_chat.send_message("Login successful.")
        return ConversationHandler.END

    async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        assert update.message is not None
        await update.message.reply_text("Cancelled.")
        return ConversationHandler.END

    # --- Admin commands --------------------------------------------------

    async def _require_admin(update: Update):
        """Return the calling User if they're an approved admin, else None
        (having already sent a rejection message to the chat).
        """
        assert update.effective_user is not None
        assert update.message is not None

        caller = await auth_service.users.get_by_telegram_id(update.effective_user.id)
        if caller is None or not caller.approved:
            await update.message.reply_text("You are not authorized to use this command.")
            return None

        try:
            await auth_service.authorize(caller, UserRole.ADMIN)
        except InsufficientPermissions:
            await update.message.reply_text("You are not authorized to use this command.")
            return None

        return caller

    async def pending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """List users awaiting approval, with their Telegram IDs."""
        assert update.message is not None

        if await _require_admin(update) is None:
            return

        all_users = await auth_service.users.list_all()
        unapproved = [u for u in all_users if not u.approved]

        if not unapproved:
            await update.message.reply_text("No users awaiting approval.")
            return

        lines = [
            f"{u.telegramId} — {u.firstName} {u.lastName or ''} (@{u.username or 'no username'})".strip()
            for u in unapproved
        ]
        await update.message.reply_text("Pending approval:\n" + "\n".join(lines))

    async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Usage: /approve <telegram_id>"""
        assert update.message is not None

        if await _require_admin(update) is None:
            return

        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text("Usage: /approve <telegram_id>")
            return

        telegram_id = int(context.args[0])
        target = await auth_service.users.get_by_telegram_id(telegram_id)
        if target is None:
            await update.message.reply_text(f"No user found with Telegram ID {telegram_id}.")
            return

        await auth_service.approve(target.id)
        await update.message.reply_text(f"Approved {target.firstName} ({telegram_id}).")

    async def setrole(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Usage: /setrole <telegram_id> <READONLY|NURSE|DOCTOR|ADMIN>"""
        assert update.message is not None

        if await _require_admin(update) is None:
            return

        if not context.args or len(context.args) != 2 or not context.args[0].isdigit():
            await update.message.reply_text(
                "Usage: /setrole <telegram_id> <READONLY|NURSE|DOCTOR|ADMIN>"
            )
            return

        telegram_id = int(context.args[0])
        role_str = context.args[1].upper()

        try:
            role = UserRole[role_str]
        except KeyError:
            await update.message.reply_text(
                "Invalid role. Choose one of: READONLY, NURSE, DOCTOR, ADMIN"
            )
            return

        target = await auth_service.users.get_by_telegram_id(telegram_id)
        if target is None:
            await update.message.reply_text(f"No user found with Telegram ID {telegram_id}.")
            return

        await auth_service.change_role(target.id, role)
        await update.message.reply_text(
            f"Set {target.firstName} ({telegram_id}) to role {role.value}."
        )

    # --- Registration ------------------------------------------------------

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_EMR_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_emr_username)
            ],
            ASK_EMR_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_emr_password)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application = ApplicationBuilder().token(settings.telegram_bot_token).build()
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("pending", pending))
    application.add_handler(CommandHandler("approve", approve))
    application.add_handler(CommandHandler("setrole", setrole))
    return application