import os
import re
import sys
import base64
import json
import binascii
from datetime import datetime
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


EVENT_URL = "https://seerm.61.com/events/17years/#sign"
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
ARTIFACT_DIR = Path(os.getenv("ARTIFACT_DIR", str(DATA_DIR / "artifacts")))
SESSION_FILE = Path(os.getenv("SESSION_FILE", str(DATA_DIR / "session.json")))
EMPTY_SESSION = {"cookies": [], "origins": []}


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def log(message: str) -> None:
    print(f"[{datetime.now().isoformat(timespec='seconds')}] {message}", flush=True)


def screenshot(page, name: str) -> Path:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTIFACT_DIR / name
    page.screenshot(path=str(path), full_page=True)
    return path


def page_text(page) -> str:
    try:
        return page.locator("body").inner_text(timeout=3000)
    except PlaywrightTimeoutError:
        return ""


def write_session_from_env() -> None:
    raw_json = os.getenv("SESSION_JSON")
    b64_json = os.getenv("SESSION_JSON_BASE64")
    if not raw_json and not b64_json:
        return

    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        if b64_json:
            normalized = b64_json.strip().strip('"').strip("'")
            normalized = re.sub(r"\s+", "", normalized)
            raw_json = base64.b64decode(normalized, validate=True).decode("utf-8")
        else:
            raw_json = (raw_json or "").strip().strip('"').strip("'")

        validate_session_json(raw_json)
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        log(f"invalid session state from environment: {exc}")
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
        return

    SESSION_FILE.write_text(raw_json, encoding="utf-8")
    log(f"session state loaded from environment into: {SESSION_FILE}")


def ensure_session_file_exists() -> bool:
    if SESSION_FILE.exists():
        return False
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(json.dumps(EMPTY_SESSION, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"created empty session file: {SESSION_FILE}")
    log("paste your generated session.json content into this file, then restart the container")
    return True


def validate_session_json(raw_json: str) -> None:
    if not raw_json.strip():
        raise ValueError("value is empty")
    data = json.loads(raw_json)
    if not isinstance(data, dict):
        raise ValueError("session JSON must be an object")
    if "cookies" not in data or "origins" not in data:
        raise ValueError("session JSON must contain cookies and origins")


def session_file_is_valid() -> bool:
    if not SESSION_FILE.exists():
        return False
    try:
        validate_session_json(SESSION_FILE.read_text(encoding="utf-8"))
        return True
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        log(f"ignoring invalid session file {SESSION_FILE}: {exc}")
        return False


def has_slider_captcha(page) -> bool:
    text = page_text(page)
    return "拖动下方拼图完成验证" in text or "安全验证" in text


def is_logged_in(page) -> bool:
    try:
        login_btn = page.locator("#J_login")
        return "logined" in (login_btn.get_attribute("class", timeout=3000) or "")
    except PlaywrightTimeoutError:
        return False


def visible_login_frames(page):
    return [frame for frame in page.frames if "account-co.61.com" in frame.url]


def login_dialog_is_open(page) -> bool:
    if visible_login_frames(page):
        return True
    selectors = [
        ".taomeesdk-dialog",
        ".taomeesdk-dialog--fixed",
        ".taomee-dialog",
    ]
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if not locator.count():
                continue
            locator.wait_for(state="visible", timeout=500)
            return True
        except PlaywrightTimeoutError:
            continue
    return False


def open_login_dialog(page) -> None:
    if login_dialog_is_open(page):
        return
    page.locator("#J_login").click(timeout=10000)
    page.wait_for_timeout(3000)


def fill_first(frame, selectors, value: str) -> bool:
    for selector in selectors:
        locator = frame.locator(selector).first
        try:
            if not locator.count():
                continue
            locator.wait_for(state="visible", timeout=1000)
            locator.fill(value, timeout=3000)
            return True
        except PlaywrightTimeoutError:
            continue
    return False


def click_first(frame, selectors) -> bool:
    for selector in selectors:
        locator = frame.locator(selector).first
        try:
            if not locator.count():
                continue
            locator.wait_for(state="visible", timeout=1000)
            locator.click(timeout=3000)
            return True
        except PlaywrightTimeoutError:
            continue
    return False


def click_mimi_login_option(page) -> None:
    labels = [
        "米米号登录",
        "米米号",
        "账号密码登录",
        "密码登录",
    ]
    for frame in visible_login_frames(page):
        for label in labels:
            try:
                target = frame.get_by_text(label, exact=False).first
                if not target.count():
                    continue
                target.wait_for(state="visible", timeout=1000)
                log(f"switching login method: {label}")
                target.click(timeout=3000)
                page.wait_for_timeout(1500)
                return
            except PlaywrightTimeoutError:
                continue


def wait_for_manual_login(page) -> bool:
    wait_seconds = int(os.getenv("LOGIN_WAIT_SECONDS", "300"))
    log(
        "manual login mode enabled; complete the visible login/captcha window "
        f"within {wait_seconds} seconds"
    )
    try:
        page.wait_for_function(
            "() => document.querySelector('#J_login')?.classList.contains('logined')",
            timeout=wait_seconds * 1000,
        )
        log("manual login detected")
        return True
    except PlaywrightTimeoutError:
        path = screenshot(page, "manual-login-timeout.png")
        log(f"manual login timed out; screenshot saved: {path}")
        return False


def close_userinfo_overlay(page) -> None:
    selectors = [
        ".uc-userinfo-back",
        ".uc-mask",
        ".taomee-dialog__closebtn",
        ".taomee-dialog__close",
    ]
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if not locator.count():
                continue
            locator.wait_for(state="visible", timeout=1000)
            locator.click(timeout=3000)
            page.wait_for_timeout(500)
        except PlaywrightTimeoutError:
            continue
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)


def try_password_login(page, mimi_id: str, password: str) -> bool:
    open_login_dialog(page)
    click_mimi_login_option(page)

    if has_slider_captcha(page):
        path = screenshot(page, "captcha.png")
        log(f"login requires slider captcha; screenshot saved: {path}")
        return False

    account_selectors = [
        "input[name='uid']",
        "input[name='account']",
        "input[name='username']",
        "input[type='text']",
        "input:not([type])",
    ]
    password_selectors = [
        "input[name='password']",
        "input[name='pwd']",
        "input[type='password']",
    ]
    submit_selectors = [
        "button[type='submit']",
        "input[type='submit']",
        "button:has-text('登录')",
        "a:has-text('登录')",
        ".login",
        ".btn-login",
    ]

    for frame in visible_login_frames(page):
        if fill_first(frame, account_selectors, mimi_id) and fill_first(frame, password_selectors, password):
            log("filled login form; submitting")
            if not click_first(frame, submit_selectors):
                frame.locator("input[type='password']").first.press("Enter")
            try:
                page.wait_for_function(
                    "() => document.querySelector('#J_login')?.classList.contains('logined')",
                    timeout=20000,
                )
                return True
            except PlaywrightTimeoutError:
                if has_slider_captcha(page):
                    path = screenshot(page, "captcha-after-submit.png")
                    log(f"captcha appeared after submit; screenshot saved: {path}")
                return is_logged_in(page)

    path = screenshot(page, "login-form-not-found.png")
    log(f"could not find a password login form; screenshot saved: {path}")
    return False


def ensure_logged_in(page) -> bool:
    if is_logged_in(page):
        return True

    if env_bool("FIRST_LOGIN_GUI", False) or not env_bool("HEADLESS", True):
        open_login_dialog(page)
        click_mimi_login_option(page)
        return wait_for_manual_login(page)

    mimi_id = os.getenv("MIMI_ID", "")
    password = os.getenv("MIMI_PASSWORD", "")
    if mimi_id and password and env_bool("ALLOW_PASSWORD_LOGIN", True):
        if try_password_login(page, mimi_id, password):
            return True

    path = screenshot(page, "not-logged-in.png")
    log(f"not logged in; screenshot saved: {path}")
    return False


def sign(page) -> int:
    close_userinfo_overlay(page)

    try:
        count_text = page.locator(".sign__count-num").inner_text(timeout=10000)
        before = int(re.sub(r"\D", "", count_text) or "0")
    except PlaywrightTimeoutError:
        before = -1

    disabled = "is-disabled" in (page.locator(".sign__btn").get_attribute("class", timeout=10000) or "")
    if disabled:
        log(f"already signed today; signed count: {before}")
        return 0

    try:
        page.locator(".sign__btn").click(timeout=10000)
    except PlaywrightTimeoutError:
        close_userinfo_overlay(page)
        page.locator(".sign__btn").click(timeout=10000)
    page.wait_for_timeout(5000)

    text = page_text(page)
    if "签到成功" in text:
        log("sign succeeded")
        return 0

    try:
        after_text = page.locator(".sign__count-num").inner_text(timeout=5000)
        after = int(re.sub(r"\D", "", after_text) or "0")
        if before >= 0 and after > before:
            log(f"sign succeeded; signed count: {after}")
            return 0
    except PlaywrightTimeoutError:
        pass

    if has_slider_captcha(page):
        path = screenshot(page, "captcha-while-signing.png")
        log(f"captcha blocked signing; screenshot saved: {path}")
        return 2

    path = screenshot(page, "sign-unknown-result.png")
    log(f"could not confirm sign result; screenshot saved: {path}")
    return 3


def main() -> int:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    write_session_from_env()
    created_empty_session = ensure_session_file_exists()
    first_login_gui = env_bool("FIRST_LOGIN_GUI", False)
    headless = env_bool("HEADLESS", not first_login_gui)
    slow_mo = int(os.getenv("SLOW_MO_MS", "0"))
    if created_empty_session and headless:
        return 2

    with sync_playwright() as p:
        browser_name = os.getenv("BROWSER", "chromium")
        browser_type = getattr(p, browser_name)
        executable_path = os.getenv("BROWSER_EXECUTABLE") or None
        browser = browser_type.launch(
            headless=headless,
            executable_path=executable_path,
            slow_mo=slow_mo,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context_kwargs = {
            "viewport": {"width": 1280, "height": 900},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
            ),
        }
        if session_file_is_valid():
            log(f"loading session state: {SESSION_FILE}")
            context_kwargs["storage_state"] = str(SESSION_FILE)
        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        page.goto(EVENT_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(8000)

        if not ensure_logged_in(page):
            log("not saving session state because login was not confirmed")
            context.close()
            browser.close()
            return 2

        result = sign(page)
        context.storage_state(path=str(SESSION_FILE))
        log(f"session state saved: {SESSION_FILE}")
        context.close()
        browser.close()
        return result


if __name__ == "__main__":
    sys.exit(main())
