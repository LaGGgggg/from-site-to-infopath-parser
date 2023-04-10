import dearpygui.dearpygui as dpg
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.service import Service as ChromeService
from subprocess import CREATE_NO_WINDOW
from os import environ
from os.path import getsize
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


DOTENV_PATH = BASE_DIR.joinpath('.env')

if DOTENV_PATH.exists():
    load_dotenv(DOTENV_PATH)

SITE_CHOICES = ('sdo-vot', 'vmig.expert')
SITE: str = environ.get('SITE', 'unset')

if SITE in SITE_CHOICES:

    if SITE == 'sdo-vot':

        SDO_VOT_DOTENV_PATH = BASE_DIR.joinpath('sdo_vot.env')

        if SDO_VOT_DOTENV_PATH.exists():
            load_dotenv(SDO_VOT_DOTENV_PATH)

    elif SITE == 'vmig.expert':

        VMIG_EXPERT_DOTENV_PATH = BASE_DIR.joinpath('vmig_expert.env')

        if VMIG_EXPERT_DOTENV_PATH.exists():
            load_dotenv(VMIG_EXPERT_DOTENV_PATH)

LOGIN_URL: str = environ.get('LOGIN_URL', 'unset')
AFTER_LOGIN_URL: str = environ.get('AFTER_LOGIN_URL', 'unset')

LOGIN_LOGIN: str = environ.get('LOGIN_LOGIN', 'unset')
LOGIN_PASSWORD: str = environ.get('LOGIN_PASSWORD', 'unset')

START_PAGE_URL: str = environ.get('START_PAGE_URL', 'unset')

LOGOUT_URL: str = environ.get('LOGOUT_URL', 'unset')
AFTER_LOGOUT_URL: str = environ.get('AFTER_LOGOUT_URL', 'unset')

QUESTIONS_THEME: str = environ.get('QUESTIONS_THEME', 'unset')

ENV_VARS = {
    'LOGIN_URL': LOGIN_URL,
    'AFTER_LOGIN_URL': AFTER_LOGIN_URL,
    'LOGIN_LOGIN': LOGIN_LOGIN,
    'LOGIN_PASSWORD': LOGIN_PASSWORD,
    'START_PAGE_URL': START_PAGE_URL,
    'LOGOUT_URL': LOGOUT_URL,
    'AFTER_LOGOUT_URL': AFTER_LOGOUT_URL,
    'SITE': SITE,
    'QUESTIONS_THEME': QUESTIONS_THEME,
}


PARSING_MODE_BUTTON_LABEL_OPTIONS: dict[str, str] = {
    'start': 'Start parsing',
    'stop': 'Stop parsing',
}

MY_NSMAP_BASE = 'http://schemas.microsoft.com/office/infopath/2003/myXSD/2005-09-12T06:50:44'
DEFAULT_NSMAP_BASE = 'http://www.w3.org/1999/xhtml'

MY_NSMAP = '{' + MY_NSMAP_BASE + '}'
DEFAULT_NSMAP = '{' + DEFAULT_NSMAP_BASE + '}'

RESULT_FILENAME: str = 'result.xml'


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

    driver.set_page_load_timeout(300)

    return driver


def update_course_themes_from_file(
        course_themes: dict[str, dict[str, dict[str, str]]] | dict[str, dict],
        filename: str,
        dpg_logger: DpgLogger) -> dict[str, dict[str, dict[str, str]]] | dict[str, dict]:

    with open(filename, 'a'):
        pass

    if getsize(filename):

        tree = etree.parse(filename).getroot()

        themes = tree.findall(f'{MY_NSMAP}temicursov/{MY_NSMAP}temacursa')

        for theme in themes:

            theme_text = theme.find(f'{MY_NSMAP}tktext').text

            course_themes[theme_text] = {}

            questions = theme.findall(f'{MY_NSMAP}questions/{MY_NSMAP}question')

            for question in questions:

                question_text: str = question.find(
                    f'{MY_NSMAP}qtext/{DEFAULT_NSMAP}div/{DEFAULT_NSMAP}span/{DEFAULT_NSMAP}strong'
                ).text

                answers = {}

                for answer in question.findall(f'{MY_NSMAP}answer'):

                    text: str = answer.find(f'{MY_NSMAP}atext/{DEFAULT_NSMAP}span').text
                    status: str = answer.find(f'{MY_NSMAP}astatus').text

                    if status not in ['Правильный ответ', 'Неправильный ответ']:

                        warning(f'Unknown answer status has been founded! ({status})')
                        dpg_logger.log_warning(f'Unknown answer status has been founded! ({status})')

                    answers[text] = status

                course_themes[theme_text][question_text] = answers

                course_themes[theme_text][question_text]['comment'] = question.find(f'{MY_NSMAP}qhelp').text

    return course_themes


def save_results_to_xml_file(
        filename: str,
        results: dict[str, dict[str, dict[str, str]]],
        dpg_logger: DpgLogger,
        log=False) -> None:

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
    etree.SubElement(main_element, f'{MY_NSMAP}curs').text = ''

    temicursov_element = etree.SubElement(main_element, f'{MY_NSMAP}temicursov')

    # Adding results into tree:
    for course_theme in results.items():

        temacursa_element = etree.SubElement(temicursov_element, f'{MY_NSMAP}temacursa')

        etree.SubElement(temacursa_element, f'{MY_NSMAP}tktext').text = course_theme[0]

        questions_element = etree.SubElement(temacursa_element, f'{MY_NSMAP}questions')

        for question in course_theme[1].items():

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

            etree.SubElement(qtext_div_span_element, 'strong').text = question[0]

            for answer in question[1].items():

                if answer[0] == 'comment':
                    continue

                answer_element = etree.SubElement(question_element, f'{MY_NSMAP}answer')

                etree.SubElement(answer_element, f'{MY_NSMAP}astatus').text = answer[1]

                atext_element = etree.SubElement(answer_element, f'{MY_NSMAP}atext')

                etree.SubElement(
                    atext_element, 'span', attrib={'xmlns': DEFAULT_NSMAP_BASE}
                ).text = answer[0]

            etree.SubElement(question_element, f'{MY_NSMAP}qhelp').text = question[1]['comment']

        etree.SubElement(temacursa_element, f'{MY_NSMAP}tkabout')

        materials_element = etree.SubElement(temacursa_element, f'{MY_NSMAP}materials')
        material_element = etree.SubElement(materials_element, f'{MY_NSMAP}material')

        etree.SubElement(material_element, f'{MY_NSMAP}name')
        etree.SubElement(material_element, f'{MY_NSMAP}filename')

        extensions_element = etree.SubElement(temacursa_element, f'{MY_NSMAP}extensions')
        extension_element = etree.SubElement(extensions_element, f'{MY_NSMAP}extension')

        etree.SubElement(extension_element, f'{MY_NSMAP}DisplayName')
        etree.SubElement(extension_element, f'{MY_NSMAP}LinkAddress')

    etree.ElementTree(main_element).write(
        filename, encoding='utf-8', xml_declaration=True, pretty_print=True
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


def sdo_vot_handler(
        driver: webdriver.Chrome,
        dpg_logger: DpgLogger,
        course_themes: dict[str, dict[str, dict[str, str]]] | dict[str, dict],
        theme_text: str) -> None:

    while True:

        if is_parser_stopped_by_user(dpg_logger):
            break

        answer_options = driver.find_elements(By.CLASS_NAME, 'checkmark')

        for answer_option in answer_options:
            answer_option.click()

        driver.find_element(By.XPATH, "//button[text()='Ответить']").click()

        WebDriverWait(driver, 10).until(
            expected_conditions.url_to_be(START_PAGE_URL), message='Answer page not loaded.'
        )

        question_text = \
            driver.find_element(By.XPATH, '/html/body/main/div/div[2]/div[2]/div/div[3]/form/div[1]/b').text

        if question_text not in course_themes[theme_text]:

            answers: dict[str, str] = {}

            bad_page = False

            answers_tags = \
                driver.find_elements(By.XPATH, '/html/body/main/div/div[2]/div[2]/div/div[3]/form/div[2]/div/label')

            for answer in answers_tags:

                answer_style = answer.get_attribute('style')

                if not answer_style:

                    info('Incorrect page, skip.')
                    dpg_logger.log_info('Incorrect page, skip.')

                    bad_page = True

                    break

                else:
                    answer_style = answer_style.split(';')[0]

                if answer_style == 'color: red':
                    answers[answer.text.replace('\n', '')] = 'Неправильный ответ'

                elif answer_style == 'color: green':
                    answers[answer.text.replace('\n', '')] = 'Правильный ответ'

                else:

                    warning(f'Unknown answer style has been founded! ({answer_style})')
                    dpg_logger.log_warning(f'Unknown answer style has been founded! ({answer_style})')

            if bad_page:
                continue

            course_themes[theme_text][question_text] = answers

            comment = ''

            try:

                comment_tags = \
                    driver.find_elements(By.XPATH, '/html/body/main/div/div[2]/div[2]/div/div[3]/form/div[3]/p')

                for comment_tag in comment_tags:
                    comment += f'\n{comment_tag.text}'

            except NoSuchElementException:
                pass

            course_themes[theme_text][question_text]['comment'] = comment

            save_results_to_xml_file(RESULT_FILENAME, course_themes, dpg_logger)

            info(f'Question saved in file ({question_text[:40]}...)')
            dpg_logger.log_info(f'Question saved in file ({question_text[:40]}...)')

        else:

            warning(f'The page has not been saved, the question has already been added. ({question_text[:40]}...)')
            dpg_logger.log_warning(
                f'The page has not been saved, the question has already been added. ({question_text[:40]}...)'
            )

        driver.find_element(By.XPATH, "//button[text()='Следующий вопрос']").click()


def vmig_expert_handler(
        driver: webdriver.Chrome,
        dpg_logger: DpgLogger,
        course_themes: dict[str, dict[str, dict[str, str]]] | dict[str, dict],
        theme_text: str) -> None:

    modal_tag = driver.find_element(By.XPATH, '/html/body/app-root/ng-component/vmig-modal/div[2]')

    question_counter: int = 0

    start_time = datetime.now()

    for question_button in driver.find_elements(By.XPATH, '/html/body/app-root/ng-component/div/section/button'):

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

        if question_text not in course_themes[theme_text]:

            answers: dict[str, str] = {}

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
                    answers[answer.text.replace('\n', '')] = 'Неправильный ответ'

                elif answer_class == 'question-html rightAnswer ng-star-inserted':
                    answers[answer.text.replace('\n', '')] = 'Правильный ответ'

                else:

                    warning(f'Unknown answer style has been founded! ({answer_class})')
                    dpg_logger.log_warning(f'Unknown answer style has been founded! ({answer_class})')

            course_themes[theme_text][question_text] = answers

            if question_content.find_element(By.XPATH, 'ul[2]').text:

                comment: str = question_content.find_element(By.XPATH, 'ul[2]').text

            else:
                comment: str = ''

            course_themes[theme_text][question_text]['comment'] = comment

            save_results_to_xml_file(RESULT_FILENAME, course_themes, dpg_logger)

            past_time = datetime.now() - start_time

            info(f'Question saved in file ({question_counter}) (past time: {past_time}) ({question_text[:40]}...)')
            dpg_logger.log_info(
                f'Question saved in file ({question_counter}) (past time: {past_time}) ({question_text[:40]}...)'
            )

        else:

            warning(f'The page has not been saved, the question has already been added.'
                    f' ({question_counter}) ({question_text[:40]}...)')
            dpg_logger.log_warning(
                f'The page has not been saved, the question has already been added.'
                f' ({question_counter}) ({question_text[:40]}...)'
            )

        modal_tag.find_element(By.CLASS_NAME, 'btn-close').click()  # close question content window

        sleep(1)


def parsing_controller(driver: webdriver.Chrome, theme_text: str, dpg_logger: DpgLogger) -> None:

    course_themes: dict[str, dict[str, dict[str, str]]] = {f'{theme_text}': {}}
    '''
    course_themes = {
        'theme text': {
            'question text': {
                'answer text': 'answer status',  # all possible statuses: 'Правильный ответ', 'Неправильный ответ'.
                'comment': 'comment text',
                ...
            },
            ...
        },
        ...
    }
    '''

    course_themes = update_course_themes_from_file(course_themes, RESULT_FILENAME, dpg_logger)

    driver.get(START_PAGE_URL)

    sleep(randint(6, 12))

    if 'Not Found' in driver.page_source or 'HTTP ERROR 404' in driver.page_source:

        error(f'404 error in page_data_handler! Parser stopped. (url: {START_PAGE_URL})')
        dpg_logger.log_error(f'404 error in page_data_handler! Parser stopped. (url: {START_PAGE_URL})')

        return

    if SITE == 'sdo-vot':
        sdo_vot_handler(driver, dpg_logger, course_themes, theme_text)

    elif SITE == 'vmig.expert':
        vmig_expert_handler(driver, dpg_logger, course_themes, theme_text)

    else:

        error(f'Bad SITE environment variable, not supported by parsing_controller. ({SITE})')
        dpg_logger.log_error(f'Bad SITE environment variable, not supported by parsing_controller. ({SITE})')


def login(driver: webdriver.Chrome, dpg_logger: DpgLogger) -> None:

    next_page_not_loaded_error_message = 'The page that should be loaded after logging in did not load. ' \
                                         'This may be because the login credentials are incorrect.'

    driver.get(LOGIN_URL)

    sleep(randint(6, 12))

    driver.find_element(By.NAME, 'login').send_keys(LOGIN_LOGIN)
    driver.find_element(By.NAME, 'password').send_keys(LOGIN_PASSWORD)

    driver.find_element(By.XPATH, "//button[text()='Войти']").click()

    WebDriverWait(driver, 10).until(
        expected_conditions.url_to_be(AFTER_LOGIN_URL), message=next_page_not_loaded_error_message
    )

    info('Login completed.')
    dpg_logger.log_info('Login completed.')


def logout(driver: webdriver.Chrome, dpg_logger: DpgLogger) -> None:

    next_page_not_loaded_error_message = 'The page that should be loaded after logging out did not load.'

    if SITE == 'sdo-vot':
        driver.get(LOGOUT_URL)

    elif SITE == 'vmig.expert':

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

    if ENV_VARS['SITE'] not in SITE_CHOICES:

        error(
            f'The environment variable "SITE" is not set! The parser is not running. Choices: {",".join(SITE_CHOICES)}'
        )
        dpg_logger.log_error(
            f'The environment variable "SITE" is not set! The parser is not running. Choices: {",".join(SITE_CHOICES)}'
        )

        return False

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

            dpg.configure_item('save_to_file_button', enabled=False)

            info('The parser has started.')
            dpg_logger.log_info('The parser has started.')

            login(driver, dpg_logger)
            parsing_controller(driver, QUESTIONS_THEME, dpg_logger)
            logout(driver, dpg_logger)

            info('The parser has finished.')
            dpg_logger.log_info('The parser has finished.')

            dpg.configure_item('save_to_file_button', enabled=True)

            dpg.configure_item('parsing_mode_button', label=PARSING_MODE_BUTTON_LABEL_OPTIONS['start'])

        else:

            dpg.configure_item('parsing_mode_button', label=PARSING_MODE_BUTTON_LABEL_OPTIONS['start'], enabled=False)

    def threading_parsing_mode_button_callback():

        t_1 = Thread(target=parsing_mode_button_callback)
        t_1.start()

    def save_to_file_button_callback():
        save_results_to_xml_file(
            f'../{RESULT_FILENAME}',
            update_course_themes_from_file({f'{QUESTIONS_THEME}': {}}, RESULT_FILENAME, dpg_logger),
            dpg_logger,
            log=True,
        )

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
        dpg.add_text(f'Logout url: {LOGOUT_URL}')
        dpg.add_text(f'After logout url: {AFTER_LOGOUT_URL}')
        dpg.add_text(f'Site: {SITE}')
        dpg.add_text(f'Questions theme: {QUESTIONS_THEME}')

        if check_env_vars_set(dpg_logger):

            dpg.add_button(
                label='Start parsing',
                callback=threading_parsing_mode_button_callback,
                tag='parsing_mode_button',
            )

            dpg.add_button(
                label='Save to file',
                callback=save_to_file_button_callback,
                tag='save_to_file_button',
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
