"""Telegram bot Application setup — webhook mode, no polling."""

from __future__ import annotations

import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler,
)

from prisma.enums import UserRole
from app.config.settings import settings
from app.auth.service import SessionAuthenticationService
from app.auth.exceptions import UserNotApproved, InsufficientPermissions
from app.emr_client.exceptions import (
    EMRLoginError,
    NoActiveEMRSession,
    EMRSessionRejected,
    ProgressNoteConversationActive,
)
from app.emr_client.search_manager import SearchSessionManager
from app.emr_client.ward_manager import WardSessionManager

logger = logging.getLogger(__name__)

# Conversation states — login flow
ASK_EMR_USERNAME, ASK_EMR_PASSWORD = range(2)

# Conversation states — progress note flow
WAITING_NOTE_TEXT, WAITING_SAVE_DECISION = range(10, 12)

# All 17 items from the Ward Management context menu (showMenu(...) RadMenu).
# Only "progress" has a real handler today (branch 2 default) — the rest
# reply "not implemented yet" when tapped, so the full menu is visible now
# and future actions (Allergy, Drug Order, etc.) reuse click_menu_item()
# without any UI rework.
WARD_ACTION_MENU: dict[str, str] = {
    "surgery": "Add Surgery",
    "admission": "Admission Form",
    "allergy": "Allergy",
    "bedxfer": "Bed Transfer",
    "bloodreq": "Blood Requisition",
    "casesheet": "Case Sheet",
    "death": "Death Summary",
    "diaghist": "Diagnostic History",
    "discharge": "Discharge Summary",
    "drugorder": "Drug Order",
    "nondrug": "Non Drug Order",
    "otreq": "OT Request",
    "dashboard": "Patient Dashboard",
    "vitals": "Patient Vitals",
    "progress": "Progress Notes",
    "provdiag": "Provisional Diagnosis",
    "referral": "Referral History",
}


def build_application(
    auth_service: SessionAuthenticationService,
    search_manager: SearchSessionManager,
    ward_manager: WardSessionManager,
) -> Application:
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

    # --- Patient Search (via SearchSessionManager) -----------------------

    def _summary_text(result) -> str:
        return (
            f"{result.name}\n"
            f"UMR: {result.umr}\n"
            f"Age/Gender: {result.age_gender}\n"
            f"Ward: {result.ward}"
        )

    async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Usage: /search <umr>"""
        assert update.message is not None
        assert update.effective_user is not None

        caller = await auth_service.users.get_by_telegram_id(update.effective_user.id)
        if caller is None or not caller.approved:
            await update.message.reply_text("You are not authorized to use this command.")
            return

        try:
            await auth_service.authorize(caller, UserRole.NURSE)
        except InsufficientPermissions:
            await update.message.reply_text("You are not authorized to use this command.")
            return

        if not context.args or not context.args[0].isdigit() or len(context.args[0]) != 7:
            await update.message.reply_text("Usage: /search <7-digit UMR number>")
            return

        umr = context.args[0]

        try:
            results, total_count = await search_manager.search(caller.id, umr)
        except NoActiveEMRSession:
            await update.message.reply_text(
                "You're not logged in to Apex. Please run /start to log in."
            )
            return
        except EMRSessionRejected:
            await update.message.reply_text(
                "Your Apex session has expired. Please run /start to log in again."
            )
            return

        if not results:
            await update.message.reply_text(f"No patient found for UMR {umr}.")
            return

        if len(results) == 1:
            selected = await search_manager.select(caller.id, 0)
            await update.message.reply_text(_summary_text(selected))
            return

        buttons = [
            [InlineKeyboardButton(f"{r.name} ({r.umr})", callback_data=f"patientsel:{r.row_index}")]
            for r in results
        ]
        prefix = ""
        if total_count > len(results):
            prefix = f"Showing {len(results)} of {total_count} results — narrow your search for more precision.\n\n"

        await update.message.reply_text(
            prefix + "Multiple matches found — select one:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    async def select_patient(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        assert update.callback_query is not None
        assert update.effective_user is not None
        query = update.callback_query
        await query.answer()

        caller = await auth_service.users.get_by_telegram_id(update.effective_user.id)
        if caller is None:
            await query.edit_message_text("Something went wrong — please /search again.")
            return

        assert query.data is not None
        row_index = int(query.data.split(":", 1)[1])

        try:
            selected = await search_manager.select(caller.id, row_index)
        except NoActiveEMRSession:
            await query.edit_message_text(
                "Search session expired — please run /search again."
            )
            return

        await query.edit_message_text(_summary_text(selected))

    # --- Ward Patient Search (via WardSessionManager) ---------------------

    def _ward_summary_text(patient) -> str:
        # Branch 11: UMR/visit_no shown here so the doctor confirms
        # identity before ever opening the action menu.
        return (
            f"👤 {patient.patient_name}\n"
            f"UMR: {patient.umr or 'unknown'}\n"
            f"Visit: {patient.visit_no or 'unknown'}\n"
            f"Age/Gender: {patient.age}\n"
            f"Admitted: {patient.admission_time}\n"
            f"Ward: {patient.ward_name}\n"
            f"Length of Stay: {patient.length_of_stay}"
        )

    def _action_menu_markup(row_index: int) -> InlineKeyboardMarkup:
        buttons = [
            [InlineKeyboardButton(text, callback_data=f"wardaction:{row_index}:{key}")]
            for key, text in WARD_ACTION_MENU.items()
        ]
        return InlineKeyboardMarkup(buttons)

    async def ward_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Usage: /ward <umr>"""
        assert update.message is not None
        assert update.effective_user is not None

        caller = await auth_service.users.get_by_telegram_id(update.effective_user.id)
        if caller is None or not caller.approved:
            await update.message.reply_text("You are not authorized to use this command.")
            return

        try:
            await auth_service.authorize(caller, UserRole.NURSE)
        except InsufficientPermissions:
            await update.message.reply_text("You are not authorized to use this command.")
            return

        if not context.args or not context.args[0].isdigit() or len(context.args[0]) != 7:
            await update.message.reply_text("Usage: /ward <7-digit UMR number>")
            return

        umr = context.args[0]

        try:
            results = await ward_manager.search_by_umr(str(caller.id), umr)
        except NoActiveEMRSession:
            await update.message.reply_text(
                "You're not logged in to Apex. Please run /start to log in."
            )
            return
        except EMRSessionRejected:
            await update.message.reply_text(
                "Your Apex session has expired. Please run /start to log in again."
            )
            return
        except ProgressNoteConversationActive:
            # Branch 7
            await update.message.reply_text(
                "You have a progress note in progress. Finish it or send /cancel first."
            )
            return

        if not results:
            await update.message.reply_text(f"No patient found in Ward Management for UMR {umr}.")
            return

        if len(results) == 1:
            # Branch 1: single result -> show summary + action menu directly.
            patient = results[0]
            await update.message.reply_text(
                _ward_summary_text(patient),
                reply_markup=_action_menu_markup(patient.row_index),
            )
            return

        buttons = [
            [
                InlineKeyboardButton(
                    f"{p.patient_name} ({p.umr or 'UMR unknown'})",
                    callback_data=f"wardpatient:{p.row_index}",
                )
            ]
            for p in results
        ]
        await update.message.reply_text(
            "Multiple patients found — select one:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    async def select_ward_patient(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """User tapped a patient from a multi-result /ward list."""
        assert update.callback_query is not None
        assert update.effective_user is not None
        query = update.callback_query
        await query.answer()

        caller = await auth_service.users.get_by_telegram_id(update.effective_user.id)
        if caller is None:
            await query.edit_message_text("Something went wrong — please /ward again.")
            return

        assert query.data is not None
        row_index = int(query.data.split(":", 1)[1])

        cached = ward_manager.get_last_results(str(caller.id))
        if cached is None:
            await query.edit_message_text(
                "Ward search session expired — please run /ward again."
            )
            return
        if row_index < 0 or row_index >= len(cached):
            await query.edit_message_text("Invalid selection.")
            return

        patient = cached[row_index]
        await query.edit_message_text(
            _ward_summary_text(patient),
            reply_markup=_action_menu_markup(patient.row_index),
        )

    async def ward_action_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        User tapped an item in the 17-item action menu.

        Only "Progress Notes" has a real handler (branch 2) — everything
        else replies "not implemented yet" and stays out of any
        ConversationHandler state.
        """
        assert update.callback_query is not None
        assert update.effective_user is not None
        assert context.user_data is not None
        query = update.callback_query
        await query.answer()

        caller = await auth_service.users.get_by_telegram_id(update.effective_user.id)
        if caller is None:
            await query.edit_message_text("Something went wrong — please /ward again.")
            return ConversationHandler.END

        assert query.data is not None
        _, row_index_str, action_key = query.data.split(":", 2)
        row_index = int(row_index_str)
        action_text = WARD_ACTION_MENU.get(action_key, action_key)

        if action_key != "progress":
            await query.edit_message_text(f"{action_text} — not implemented yet.")
            return ConversationHandler.END

        user_id = str(caller.id)

        try:
            await ward_manager.open_progress_notes_for_patient(user_id, row_index)
        except NoActiveEMRSession:
            await query.edit_message_text(
                "You're not logged in to Apex. Please run /start to log in."
            )
            return ConversationHandler.END
        except IndexError:
            await query.edit_message_text(
                "That selection is no longer valid — please run /ward again."
            )
            return ConversationHandler.END
        except Exception:
            logger.exception("Failed to open Progress Notes for user %s", user_id)
            await query.edit_message_text(
                "Couldn't open Progress Notes for this patient. Please try again."
            )
            return ConversationHandler.END

        context.user_data["pn_row_index"] = row_index

        await query.edit_message_text("Progress Notes opened.")
        # Branch 10: free text can't be solicited via an edited button
        # message, so a fresh message is sent for this step.
        assert update.effective_chat is not None
        await update.effective_chat.send_message(
            "Type your progress note as a message. It will be saved with a "
            "DWR timestamp prefix automatically. Send /cancel to abort."
        )
        return WAITING_NOTE_TEXT

    async def receive_progress_note_text(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        assert update.message is not None and update.message.text is not None
        assert update.effective_user is not None
        assert update.effective_chat is not None
        assert context.user_data is not None

        caller = await auth_service.users.get_by_telegram_id(update.effective_user.id)
        if caller is None:
            await update.message.reply_text("Something went wrong — please /ward again.")
            return ConversationHandler.END

        user_id = str(caller.id)
        note_text = update.message.text.strip()
        context.user_data["pn_note_text"] = note_text

        await update.message.reply_text("Saving note...")
        return await _attempt_save(update.effective_chat, context, user_id)

    async def _attempt_save(chat, context: ContextTypes.DEFAULT_TYPE, user_id: str) -> int:
        """Shared by first save attempt and retry (branch 5)."""
        assert context.user_data is not None
        note_text = context.user_data.get("pn_note_text", "")

        try:
            await ward_manager.fill_progress_note(user_id, note_text)
            result = await ward_manager.save_progress_note(user_id)
        except NoActiveEMRSession:
            await chat.send_message(
                "You're not logged in to Apex. Please run /start to log in."
            )
            return ConversationHandler.END
        except Exception:
            logger.exception("Error while saving progress note for user %s", user_id)
            await chat.send_message(
                "Something went wrong while saving. The popup was left open — "
                "please check the EMR directly, then send /cancel."
            )
            return WAITING_SAVE_DECISION

        if result.success:
            await ward_manager.close_progress_note(user_id)
            await chat.send_message(f"Progress note saved: {result.message}")
            context.user_data.pop("pn_row_index", None)
            context.user_data.pop("pn_note_text", None)
            return ConversationHandler.END

        # Branch 5: save didn't confirm — capture diagnostics, leave popup
        # open, offer retry or cancel. Caller (doctor) decides which.
        try:
            diagnostics = await ward_manager.capture_progress_note_failure_diagnostics(
                user_id
            )
            logger.warning(
                "Progress note save unconfirmed for user %s. Popup HTML: %s",
                user_id,
                diagnostics.popup_html,
            )
            await chat.send_photo(
                photo=diagnostics.screenshot_bytes,
                caption="Save didn't confirm — here's the current popup state.",
            )
        except Exception:
            logger.exception(
                "Failed to capture failure diagnostics for user %s", user_id
            )

        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Retry save", callback_data="pnretry"),
                    InlineKeyboardButton("Cancel", callback_data="pncancel"),
                ]
            ]
        )
        await chat.send_message(
            "Save didn't confirm. Retry, or cancel and check the EMR directly?",
            reply_markup=buttons,
        )
        return WAITING_SAVE_DECISION

    async def save_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        assert update.callback_query is not None
        assert update.effective_user is not None
        assert update.effective_chat is not None
        assert context.user_data is not None
        query = update.callback_query
        await query.answer()

        caller = await auth_service.users.get_by_telegram_id(update.effective_user.id)
        if caller is None:
            await query.edit_message_text("Something went wrong — please /ward again.")
            return ConversationHandler.END

        user_id = str(caller.id)

        if query.data == "pnretry":
            await query.edit_message_text("Retrying save...")
            return await _attempt_save(update.effective_chat, context, user_id)

        # pncancel
        try:
            await ward_manager.cancel_progress_note(user_id)
        except Exception:
            logger.exception(
                "Failed to close Progress Notes popup on cancel for user %s", user_id
            )
        context.user_data.pop("pn_row_index", None)
        context.user_data.pop("pn_note_text", None)
        await query.edit_message_text(
            "Cancelled. The popup was closed without saving — please verify "
            "in the EMR directly if needed."
        )
        return ConversationHandler.END

    async def cancel_progress_note_flow(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Fallback /cancel while inside the progress-note ConversationHandler."""
        assert update.message is not None
        assert update.effective_user is not None
        assert context.user_data is not None

        caller = await auth_service.users.get_by_telegram_id(update.effective_user.id)
        if caller is not None:
            user_id = str(caller.id)
            try:
                await ward_manager.cancel_progress_note(user_id)
            except Exception:
                logger.exception(
                    "Failed to close Progress Notes popup on /cancel for user %s",
                    user_id,
                )

        context.user_data.pop("pn_row_index", None)
        context.user_data.pop("pn_note_text", None)
        await update.message.reply_text("Cancelled. The popup was closed without saving.")
        return ConversationHandler.END

    # --- Registration ------------------------------------------------------

    login_conv_handler = ConversationHandler(
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

    progress_note_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(ward_action_selected, pattern=r"^wardaction:\d+:\w+$")
        ],
        states={
            WAITING_NOTE_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_progress_note_text)
            ],
            WAITING_SAVE_DECISION: [
                CallbackQueryHandler(save_decision, pattern=r"^pnretry$|^pncancel$")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_progress_note_flow)],
    )

    application = ApplicationBuilder().token(settings.telegram_bot_token).build()
    application.add_handler(login_conv_handler)
    application.add_handler(CommandHandler("pending", pending))
    application.add_handler(CommandHandler("approve", approve))
    application.add_handler(CommandHandler("setrole", setrole))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CallbackQueryHandler(select_patient, pattern=r"^patientsel:\d+$"))

    application.add_handler(CommandHandler("ward", ward_search))
    application.add_handler(
        CallbackQueryHandler(select_ward_patient, pattern=r"^wardpatient:\d+$")
    )
    # Must be added after ward_search/select_ward_patient; the progress-note
    # ConversationHandler owns the "wardaction:*" callback pattern as its
    # entry point.
    application.add_handler(progress_note_conv_handler)

    return application