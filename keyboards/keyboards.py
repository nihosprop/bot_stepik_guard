from keyboards.kb_utils import create_static_kb
from keyboards.buttons import (BUTTS_OWN_START,
                               BUTTS_SETTINGS_COURSES,
                               BUTTS_SETTINGS_USERS,
                               BUTTS_USER_START)

kb_own_start = create_static_kb(**BUTTS_OWN_START, cancel_butt=False)

