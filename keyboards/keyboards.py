from keyboards.kb_utils import create_static_kb
from keyboards.buttons import (BUTTS_ALL_SETTINGS,
                               BUTTS_OWN_START,
                               BUTTS_SETTINGS_COURSES,
                               BUTTS_SETTINGS_USERS,
                               BUTTS_USER_START)

kb_exit = create_static_kb(cancel_butt=False, exit_=True)

kb_own_start = create_static_kb(**BUTTS_OWN_START, cancel_butt=False)
kb_user_start = create_static_kb(**BUTTS_USER_START, cancel_butt=False)

kb_settings_users = create_static_kb(**BUTTS_SETTINGS_USERS, cancel_butt=True)
kb_add_del_user = create_static_kb(back=True, cancel_butt=True)

kb_settings_courses = create_static_kb(
    **BUTTS_SETTINGS_COURSES, cancel_butt=True)
kb_add_del_course = create_static_kb(back=True, cancel_butt=True)

kb_all_settings = create_static_kb(**BUTTS_ALL_SETTINGS)
