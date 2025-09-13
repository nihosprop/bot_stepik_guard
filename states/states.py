import logging
from aiogram.fsm.state import State, StatesGroup

logger = logging.getLogger(__name__)

class UsersSettingsStates(StatesGroup):
    settings_users = State()
    fill_tg_user_id_add = State()
    fill_tg_user_id_delete = State()

class CoursesSettingsStates(StatesGroup):
    settings_courses = State()
    fill_course_id_add = State()
    fill_course_id_delete = State()

class AllSettingsStates(StatesGroup):
    user_settings = State()
