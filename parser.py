import dearpygui.dearpygui as dpg
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.chrome.service import Service as ChromeService
from subprocess import CREATE_NO_WINDOW
from os import environ
from dotenv import load_dotenv
from pathlib import Path
from time import sleep
from random import randint
from threading import Thread
from lxml import etree
from logging import getLogger, info, warning, error, basicConfig, INFO
from dearpygui_ext.logger import mvLogger as DpgLogger
from selenium.webdriver.common.action_chains import ActionChains
from datetime import datetime


basicConfig(level=INFO)
logger = getLogger(__name__)


BASE_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = BASE_DIR.joinpath('output')


DOTENV_PATH = BASE_DIR.joinpath('.env')

if DOTENV_PATH.exists():
    load_dotenv(DOTENV_PATH)


LOGIN_URL: str = environ.get('LOGIN_URL', 'unset')
AFTER_LOGIN_URL: str = environ.get('AFTER_LOGIN_URL', 'unset')

login_logins_raw = []

# remove empty values:
for login in environ.get('LOGIN_LOGINS', 'unset').replace(' ', '').split('\n'):

    if login == 'unset':

        login_logins_raw = 'unset'

        break

    if login:
        login_logins_raw.append(login)


LOGIN_LOGINS: list[str] | str = login_logins_raw

login_passwords_raw = []

# remove empty values:
for password in environ.get('LOGIN_PASSWORDS', 'unset').replace(' ', '').split('\n'):

    if password == 'unset':

        login_passwords_raw = 'unset'

        break

    if password:
        login_passwords_raw.append(password)

LOGIN_PASSWORDS: list[str] | str = login_passwords_raw

START_PAGE_URL: str = environ.get('START_PAGE_URL', 'unset')

AFTER_LOGOUT_URL: str = environ.get('AFTER_LOGOUT_URL', 'unset')

ENV_VARS = {
    'LOGIN_URL': LOGIN_URL,
    'AFTER_LOGIN_URL': AFTER_LOGIN_URL,
    'LOGIN_LOGINS': LOGIN_LOGINS,
    'LOGIN_PASSWORDS': LOGIN_PASSWORDS,
    'START_PAGE_URL': START_PAGE_URL,
    'AFTER_LOGOUT_URL': AFTER_LOGOUT_URL,
}


PARSING_MODE_BUTTON_LABEL_OPTIONS: dict[str, str] = {
    'start': 'Start parsing',
    'stop': 'Stop parsing',
}

MY_NSMAP_BASE = 'http://schemas.microsoft.com/office/infopath/2003/myXSD/2005-09-12T06:50:44'
DEFAULT_NSMAP_BASE = 'http://www.w3.org/1999/xhtml'

MY_NSMAP = '{' + MY_NSMAP_BASE + '}'
DEFAULT_NSMAP = '{' + DEFAULT_NSMAP_BASE + '}'

CURRENT_WORK_FILENAME = '_current_work.txt'
CURRENT_WORK_FILE_PATH = BASE_DIR.joinpath('results', CURRENT_WORK_FILENAME)

COURSE_STATUSES = {
    'waiting': 'waiting',
    'completed': 'completed',
}


def get_driver() -> webdriver.Chrome:

    chrome_options = webdriver.ChromeOptions()

    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    chrome_options.add_argument('disable-infobars')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--disable-popup-blocking')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--dns-prefetch-disable')
    chrome_options.add_argument('ignore-certificate-errors')
    chrome_options.add_argument('--lang=en-US')
    chrome_options.add_argument('--mute-audio')

    chrome_options.set_capability('unhandledPromptBehavior', 'dismiss')

    prefs = {
        'profile.managed_default_content_settings.images': 2,
        'profile.default_content_setting_values.notifications': 2,
    }

    chrome_options.add_experimental_option('prefs', prefs)

    chrome_service = ChromeService('chromedriver')

    chrome_service.creationflags = CREATE_NO_WINDOW

    driver = webdriver.Chrome(options=chrome_options, service=chrome_service)

    driver.maximize_window()

    driver.set_page_load_timeout(300)

    return driver


"""
course = {
    'course_name': 'example_course_name',
    'questions': [
        {
            'question_text': 'example_question_text',
            'comment': 'example_question_comment',
            'answers': [
                {'answer_text': 'example_answer_text', 'is_correct': 'Правильный ответ'},
                ...
            ],
        },
        ...
    ]
}
"""


def save_course_to_xml_file(
        course: dict[str: str, str: list[dict[str: str, str: list[dict[str: str]]]]],
        dpg_logger: DpgLogger,
        log=False
) -> None:

    main_element = etree.Element(
        f'{MY_NSMAP}field', nsmap={'my': MY_NSMAP_BASE}, attrib={'{http://www.w3.org/XML/1998/namespace}lang': 'ru'}
    )

    # Processing instructions:
    mso_info_path_solution_text = \
        r'PIVersion="1.0.0.0" href="file:///C:\curs.xsn" productVersion="12.0.0" solutionVersion="1.0.0.73"'

    main_element.addprevious(
        etree.ProcessingInstruction('mso-infoPathSolution', text=mso_info_path_solution_text)
    )
    main_element.addprevious(
        etree.ProcessingInstruction('mso-application', text='progid="InfoPath.Document"')
    )

    # Unique tree elements building:
    etree.SubElement(main_element, f'{MY_NSMAP}curs').text = course['course_name']

    temicursov_element = etree.SubElement(main_element, f'{MY_NSMAP}temicursov')

    temacursa_element = etree.SubElement(temicursov_element, f'{MY_NSMAP}temacursa')

    etree.SubElement(temacursa_element, f'{MY_NSMAP}tktext').text = course['course_name']

    questions_element = etree.SubElement(temacursa_element, f'{MY_NSMAP}questions')

    for question in course['questions']:

        if not question['answers']:
            continue

        question_element = etree.SubElement(questions_element, f'{MY_NSMAP}question')

        qtext_element = etree.SubElement(question_element, f'{MY_NSMAP}qtext')

        qtext_div_attribs = {
            'style': 'MARGIN-TOP: 0cm; PADDING-LEFT: 0cm; PADDING-RIGHT: 0cm; MARGIN-BOTTOM: 0pt',
            'align': 'center',
            'xmlns': DEFAULT_NSMAP_BASE,
        }

        qtext_div_element = etree.SubElement(
            qtext_element, 'div', attrib=qtext_div_attribs
        )

        qtext_div_span_element = etree.SubElement(qtext_div_element, 'span')

        etree.SubElement(qtext_div_span_element, 'strong').text = question['question_text']

        for answer in question['answers']:

            answer_element = etree.SubElement(question_element, f'{MY_NSMAP}answer')

            etree.SubElement(answer_element, f'{MY_NSMAP}astatus').text = answer['is_correct']

            atext_element = etree.SubElement(answer_element, f'{MY_NSMAP}atext')

            etree.SubElement(
                atext_element, 'span', attrib={'xmlns': DEFAULT_NSMAP_BASE}
            ).text = answer['answer_text']

        etree.SubElement(question_element, f'{MY_NSMAP}qhelp').text = question['comment']

    etree.SubElement(temacursa_element, f'{MY_NSMAP}tkabout')

    materials_element = etree.SubElement(temacursa_element, f'{MY_NSMAP}materials')
    material_element = etree.SubElement(materials_element, f'{MY_NSMAP}material')

    etree.SubElement(material_element, f'{MY_NSMAP}name')
    etree.SubElement(material_element, f'{MY_NSMAP}filename')

    extensions_element = etree.SubElement(temacursa_element, f'{MY_NSMAP}extensions')
    extension_element = etree.SubElement(extensions_element, f'{MY_NSMAP}extension')

    etree.SubElement(extension_element, f'{MY_NSMAP}DisplayName')
    etree.SubElement(extension_element, f'{MY_NSMAP}LinkAddress')

    course_name_short = course['course_name']

    if len(course_name_short) > 240:

        course_name_short = course_name_short[:200]
        warning(f'Too long name founded: "{course["course_name"]}"')

    filename = f"{course_name_short}.xml".replace('..', '.')  # replace prevent from this: "filename..xml"

    # \\\\?\\ is needed for the long filenames
    etree.ElementTree(main_element).write(
        f'\\\\?\\{OUTPUT_DIR.joinpath(filename)}', encoding='utf-8', xml_declaration=True, pretty_print=True
    )

    if log:
        info(f'Data successfully saved to: {filename}')
        dpg_logger.log_info(f'Data successfully saved to: {filename}')


def is_parser_stopped_by_user(dpg_logger: DpgLogger) -> bool:

    if dpg.get_item_label('parsing_mode_button') == PARSING_MODE_BUTTON_LABEL_OPTIONS['start']:

        dpg.configure_item('parsing_mode_button', enabled=True)

        info('Parser stopped by user.')
        dpg_logger.log_info('Parser stopped by user.')

        return True

    return False


def do_login(driver: webdriver.Chrome, dpg_logger: DpgLogger, login: str, password: str) -> None:

    next_page_not_loaded_error_message = 'The page that should be loaded after logging in did not load. ' \
                                         'This may be because the login credentials are incorrect.'

    driver.get(LOGIN_URL)

    sleep(randint(6, 12))

    driver.find_element(By.NAME, 'login').send_keys(login)
    driver.find_element(By.NAME, 'password').send_keys(password)

    driver.find_element(By.XPATH, "//button[text()='Войти']").click()

    sleep(randint(6, 12))

    WebDriverWait(driver, 0).until(
        expected_conditions.url_to_be(AFTER_LOGIN_URL), message=next_page_not_loaded_error_message
    )

    info('Login completed.')
    dpg_logger.log_info('Login completed.')


def parse(driver: webdriver.Chrome, dpg_logger: DpgLogger) -> None:

    for login, password in zip(LOGIN_LOGINS, LOGIN_PASSWORDS):

        do_login(driver, dpg_logger, login, password)

        if not driver.current_url == START_PAGE_URL:

            driver.get(START_PAGE_URL)

            sleep(randint(6, 12))

            WebDriverWait(driver, 0).until(
                expected_conditions.url_to_be(AFTER_LOGIN_URL),
                message=f'The page that should be loaded did not load (url: {START_PAGE_URL}).',
            )

        course_elements_length = \
            len(driver.find_elements(By.XPATH, '/html/body/app-root/ng-component/div/section/div/a'))

        for course_element_i in range(course_elements_length):

            driver.find_elements(
                By.XPATH, '/html/body/app-root/ng-component/div/section/div/a'
            )[course_element_i].click()

            sleep(randint(6, 12))

            course = {'course_name': driver.find_element(By.CLASS_NAME, 'course-box-title').text}

            info(f'Start course parsing ("{course["course_name"]}")')
            dpg_logger.log_info(f'Start course parsing ("{course["course_name"]}")')

            questions_button = \
                driver.find_element(By.XPATH, '/html/body/app-root/ng-component/div/section/div[3]/button')

            driver.execute_script("arguments[0].click();", questions_button)

            sleep(randint(6, 12))

            modal_tag = driver.find_element(By.XPATH, '/html/body/app-root/ng-component/vmig-modal/div[2]')

            question_counter: int = 0
            course['questions'] = []

            question_buttons = driver.find_elements(By.XPATH, '/html/body/app-root/ng-component/div/section/button')

            start_time = datetime.now()

            for question_button in question_buttons:

                question_counter += 1

                if is_parser_stopped_by_user(dpg_logger):
                    break

                actions = ActionChains(driver)

                actions.move_to_element(question_button).perform()

                question_button.click()  # open question content window

                sleep(1)

                question_content = driver.find_element(
                    By.XPATH, '/html/body/app-root/ng-component/vmig-modal/div[2]/student-question/div[2]'
                )

                question_text: str = question_content.find_element(By.TAG_NAME, 'p').text

                answers: list[dict[str: str]] = []

                answers_elements = question_content.find_elements(By.XPATH, 'ul[1]/li')

                if not answers_elements:

                    info(f'No answers to the question, skip it. ({question_counter}) ({question_text})')
                    dpg_logger.log_info(f'No answers to the question, skip it. ({question_counter}) ({question_text})')

                    modal_tag.find_element(By.CLASS_NAME, 'btn-close').click()  # close question content window

                    sleep(1)

                    continue

                for answer in answers_elements:

                    answer_class = answer.get_attribute('class')

                    if answer_class == 'question-html ng-star-inserted':
                        answers.append(
                            {
                                'answer_text': answer.text.replace('\n', ''),
                                'is_correct': 'Неправильный ответ',
                            }
                        )

                    elif answer_class == 'question-html rightAnswer ng-star-inserted':
                        answers.append(
                            {
                                'answer_text': answer.text.replace('\n', ''),
                                'is_correct': 'Правильный ответ',
                            }
                        )

                    else:

                        warning(f'Unknown answer style has been founded! ({answer_class})')
                        dpg_logger.log_warning(f'Unknown answer style has been founded! ({answer_class})')

                comment: str = question_content.find_element(By.XPATH, 'ul[2]').text or ''

                course['questions'].append(
                    {
                        'question_text': question_text,
                        'comment': comment,
                        'answers': answers,
                    }
                )

                past_time = datetime.now() - start_time

                info(f'Question saved ({question_counter}) (past time: {past_time}) ({question_text[:40]}...)')
                dpg_logger.log_info(
                    f'Question saved ({question_counter}) (past time: {past_time}) ({question_text[:40]}...)'
                    )

                modal_tag.find_element(By.CLASS_NAME, 'btn-close').click()  # close question content window

                sleep(1)

            save_course_to_xml_file(course, dpg_logger)

            info(f'Course saved ("{course["course_name"]}")')
            dpg_logger.log_info(f'Course saved ("{course["course_name"]}")')

            driver.get(START_PAGE_URL)

            WebDriverWait(driver, 10).until(
                expected_conditions.alert_is_present(),
                message='Expected alert did not load',
            )

            driver.switch_to.alert.accept()

            sleep(randint(6, 12))

            WebDriverWait(driver, 0).until(
                expected_conditions.url_to_be(AFTER_LOGIN_URL),
                message=f'The page that should be loaded did not load (url: {START_PAGE_URL}).',
            )


def logout(driver: webdriver.Chrome, dpg_logger: DpgLogger) -> None:

    next_page_not_loaded_error_message = 'The page that should be loaded after logging out did not load.'

    driver.get(AFTER_LOGIN_URL)

    sleep(randint(6, 12))

    driver.find_element(By.ID, 'navbarDropdown2').click()
    driver.find_element(By.XPATH, "//a[text()='Выход']").click()

    WebDriverWait(driver, 10).until(
        expected_conditions.url_to_be(AFTER_LOGOUT_URL), message=next_page_not_loaded_error_message
    )

    info('Logout completed.')
    dpg_logger.log_info('Logout completed.')


def check_env_vars_set(dpg_logger: DpgLogger) -> bool:

    for env_var in ENV_VARS.items():
        if env_var[1] in ('unset', '', ' '):

            error(f'The environment variable "{env_var[0]}" is not set! The parser is not running.')
            dpg_logger.log_error(f'The environment variable "{env_var[0]}" is not set! The parser is not running.')

            return False

    return True


def set_up_gui(driver: webdriver.Chrome) -> None:

    def parsing_mode_button_callback():

        if dpg.get_item_label('parsing_mode_button') == PARSING_MODE_BUTTON_LABEL_OPTIONS['start']:

            dpg.configure_item('parsing_mode_button', label=PARSING_MODE_BUTTON_LABEL_OPTIONS['stop'])

            info('The parser has started.')
            dpg_logger.log_info('The parser has started.')

            parse(driver, dpg_logger)
            logout(driver, dpg_logger)

            info('The parser has finished.')
            dpg_logger.log_info('The parser has finished.')

            dpg.configure_item('parsing_mode_button', label=PARSING_MODE_BUTTON_LABEL_OPTIONS['start'])

        else:

            dpg.configure_item('parsing_mode_button', label=PARSING_MODE_BUTTON_LABEL_OPTIONS['start'], enabled=False)

    def threading_parsing_mode_button_callback():

        t_1 = Thread(target=parsing_mode_button_callback)
        t_1.start()

    dpg.create_context()

    with dpg.font_registry():
        with dpg.font('default.ttf', 18) as default_font:
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Cyrillic)

    with dpg.window(tag='main_window'):

        dpg.bind_font(default_font)

        with dpg.window(tag='logger_window', label='App logger', width=500, height=625, pos=(575, 10), collapsed=True):

            dpg_logger = DpgLogger(parent='logger_window')

            dpg_logger.log_info('Logger has started')

        dpg.add_text(f'Parse from: {START_PAGE_URL}')
        dpg.add_text(f'Login url: {LOGIN_URL}')
        dpg.add_text(f'After login url: {AFTER_LOGIN_URL}')
        dpg.add_text(f'After logout url: {AFTER_LOGOUT_URL}')
        dpg.add_text(f'Login logins: {LOGIN_LOGINS}')

        if check_env_vars_set(dpg_logger):
            dpg.add_button(
                label='Start parsing',
                callback=threading_parsing_mode_button_callback,
                tag='parsing_mode_button',
            )

    dpg.create_viewport(title='Super parser', width=1100, height=700)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window('main_window', True)


def main() -> None:

    info('The program has started.')

    driver = get_driver()

    set_up_gui(driver)

    dpg.start_dearpygui()

    dpg.destroy_context()

    driver.quit()

    info('The program has ended.')


if __name__ == '__main__':
    main()
