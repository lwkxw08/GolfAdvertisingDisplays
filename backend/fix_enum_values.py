from app.database import get_db, NoticeStyle
from sqlalchemy import text

def fix_font_enum_values():
    db = next(get_db())
    try:
        result = db.execute(text('UPDATE notice_styles SET font_family = UPPER(font_family) WHERE font_family != UPPER(font_family)'))
        db.commit()
        print(f'Fixed {result.rowcount} font_family values in notice_styles table')
    except Exception as e:
        print(f'Error: {e}')
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_font_enum_values()
