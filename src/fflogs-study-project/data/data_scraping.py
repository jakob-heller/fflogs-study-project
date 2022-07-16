"""Includes implementation of Scraping class."""

import time
import os
import re

from bs4 import BeautifulSoup
from selenium import webdriver

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException


class Scraping:
    """Implementation of all necessary scraping methods.

    Attributes:
      logs:
        A list of logs (urls) to be scraped.
      enc_type:
        A string indicating what encounters should be taken into account -
        "all" encounters, only "kills" or only "wipes".
      driver:
        Firefox webdriver object.
      cookies:
        A boolean that is true if cookies are to be accepted during the
        scraping operation. This parameter exists because the cookie pop-up
        could in theory obscure the csv download button we want to click on.
        (does not happen unless manually induced)
      comp:
        8-tuple of strings, representing job(/class)-composition in logs.
    """

    def __init__(self,
                 logs: list[str],
                 type: str,
                 headless: bool,
                 cookies: bool = False):
        """Initializes object with given attributes, start driver.

        Args:
          logs:
            A list of strings (urls); links to logs that have been inputted by
            the user.
          encounters_type:
            A string indicating what encounters should be taken into account,
            as inputted by the user.
          headless:
            A boolean that is true if the Webdriver is to be started headless
            (-> invisible) and false if not, as inputted by the user.
        """
        self.logs = logs
        self.comp = ()
        self.enc_type = type

        options = webdriver.FirefoxOptions()
        if headless:
            options.headless = True

        # Before scraping new data, we first need to clear out old csv files.
        dirname = os.path.dirname(__file__)
        csv_path = os.path.join(dirname, "csv")
        for filename in os.listdir(csv_path):
            file_path = os.path.join(csv_path, filename)
            os.unlink(file_path)

        # In order to automatically download csv files, we need to create a
        # FirefoxProfile and adjust our download preferences.
        ffprofile = webdriver.FirefoxProfile()
        ffprofile.set_preference("browser.download.folderList", 2)
        ffprofile.set_preference("browser.download.manager.showWhenStarting", False)
        ffprofile.set_preference("browser.download.dir", csv_path)
        ffprofile.set_preference("browser.helperApps.neverAsk.saveToDisk", "csv")

        # Start Firefox driver with options (headless or not) and profile.
        self.driver = webdriver.Firefox(ffprofile, options=options,
                                        executable_path="geckodriver.exe")

        # Since the website loads a large amount of adds, loading can take
        # pretty long - but we can significantly reduce runtime by installing
        # an adblocker. This also allows selenium to click on elements, because
        # we don't risk buttons being obscured by pop-ups, which makes locating
        # elements much easier.
        # We install our adblocker (ublock origin) from an xpi file and
        # activate it by adding it to our FirefoxProfile.
        self.driver.install_addon("ublock_origin-1.43.0.xpi", temporary=True)
        ffprofile.add_extension(extension="ublock_origin-1.43.0.xpi")

    def parse_logs(self) -> None:
        """Parses and scrapes all given logs."""
        counter = 1
        max = len(self.logs)
        for log in self.logs:
            print(f"Beginning log {counter}/{max}... ", flush=True, end=" ")
            self.to_summary(log)
            if not self.check_comp(self.get_comp()):
                print("...will be left out, group comp is invalid.")
                continue
            self.to_damage_dealt()
            self.get_damage_dealt()
            self.to_healing_done()
            self.get_healing_done()
            print(f"...log {counter}/{max} finished.")
            counter += 1
        # We wait a split second at the end to make sure downloads are finished
        time.sleep(0.5)
        self.quit()

    def quit(self) -> None:
        """Closes browser/ quits driver."""
        self.driver.quit()

    def wait_until(self, value: str, timeout: int = 10, by=By.XPATH):
        """Waits till element is loaded.

        This is a helper function, called by most other scraping methods.
        Elements take inconsistent times to load, so we need some kind of
        dynamic waiting time which we use WebDriverWait for.

        Args:
          value:
            A string by which we try locating the element (xpath or class).
          timeout:
            An integer, the amount of maximum seconds to wait until timeout.
          by:
            Takes attributes of Seleniums By class. We use it to specify by
            by what value we want to locate our element (xpath or class name).

        Returns:
          Object of Seleniums WebElement class.
        """
        ignored_exceptions = (NoSuchElementException, StaleElementReferenceException,)
        return (WebDriverWait(self.driver,
                              timeout=timeout,
                              ignored_exceptions=ignored_exceptions)
                .until(EC.presence_of_element_located((by, value))))

    def to_summary(self, log_url: str) -> None:
        """Modifies given url and opens summary page."""
        url = (log_url + "#boss=-2")

        if self.enc_type == "wipes":
            url = (url + "&wipes=1")
        elif self.enc_type == "kills":
            url = (url + "&wipes=2")
        # fflogs.com interprets urls without those additions as "all"
        # encounters, so we don't need to do anything in that case.
        self.driver.get(url)

    def get_comp(self) -> str:
        """Gets html of summary page an returns the composition table."""
        self.wait_until("//table[@class='composition-table']")

        parsed_summary = BeautifulSoup(self.driver.page_source, "html.parser")
        comp_html = parsed_summary.find_all(class_="composition-entry")
        return str(comp_html)

    def check_comp(self, comp_html: str) -> bool:
        """Parses html string with regex and checks group composition.

        Args:
          comp_html:
            A string of everything labeled with class="composition-enrty" in
            the page html.

        Returns:
          False if the composition tuple created shows a different group
          composition than present in the previous logs, true otherwise.
        """
        comp = list(re.findall("\"[a-zA-Z]*\"", comp_html))
        comp = [s.strip('"') for s in comp]

        # Compare given composition with comp attribute.
        if len(self.comp) > 0 and sorted(self.comp) != sorted(tuple(comp)):
            return False
        else:
            self.comp = tuple(comp)
            return True

    def to_damage_dealt(self) -> None:
        """Navigates from "summary" to "damage dealt" tab."""
        sum_url = self.driver.current_url
        dd_url = (sum_url + "&type=damage-done")
        self.driver.get(dd_url)

    def get_damage_dealt(self) -> None:
        """Downloads csv from damage tab."""
        html_class = "buttons-csv"
        self.wait_until(html_class, by=By.CLASS_NAME).send_keys(Keys.ENTER)

    def to_healing_done(self) -> None:
        """Navigates from "damage dealt" to "healing" tab."""
        dd_url = self.driver.current_url
        hd_url = dd_url.replace("&type=damage-done", "&type=healing")
        self.driver.get(hd_url)

        # self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def get_healing_done(self) -> None:
        """Downloads csv from healing tab."""
        time.sleep(0.5)
        html_class = "buttons-csv"
        self.wait_until(html_class, by=By.CLASS_NAME).send_keys(Keys.ENTER)
