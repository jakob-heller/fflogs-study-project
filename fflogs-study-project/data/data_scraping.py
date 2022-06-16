"""Includes implementation of Scraping class."""

import re
import time
import pandas as pd

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options

from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)


class Scraping:
    """Implementation of all necessary scraping methods.

    Attributes:
      logs: list of logs (links) to be scraped.
      enc_type: int indicating what encounters should be taken into account.
      driver: Firefox webdriver object.

      comp: 8-tuple of job-composition in logs.
      dd_dfs: list containing damage dealt pandas dataframes.
      hd_dfs: list containing healing done pandas dataframes.
    """

    def __init__(self, logs: list, encounters_type: str, headless=True):
        """Initialize object with given attributes, start driver.

        Args:
          logs: list of log links (user input)
          encounters_type: include either wipes, kills or all encounters.
          headless: True if browser should be invisible, false if visible.
        """
        self.logs = logs
        self.comp = ()
        self.dd_dfs = list()
        self.hd_dfs = list()

        if encounters_type == "wipes":
            self.enc_type = 0
        elif encounters_type == "kills":
            self.enc_type = 1
        elif encounters_type == "all":
            self.enc_type = 2
        else:
            raise AttributeError("Select a valid encounter type.")

        options = Options()
        if headless:
            options.headless = True
        self.driver = webdriver.Firefox(options=options)

        logging.info(f"{datetime.now().time()}: Scraping object created.")

    def quit(self):
        """Close browser/ quit driver."""
        self.driver.quit()

        logging.info(f"{datetime.now().time()}: Driver quit.")

    def first_popup(self):
        """Need to accept pop-up when visiting fflogs for the first time."""
        self.driver.get("https://www.fflogs.com/")

        logging.info(f"{datetime.now().time()}: Navigated to first popup.")

        time.sleep(0.5)

        popup_xp = "/html/body/div[2]/div/div/div/div[2]/div/button[1]"
        self.driver.find_element(By.XPATH, popup_xp).send_keys(Keys.ENTER)

        logging.info(f"{datetime.now().time()}: First popup accepted.")

    def to_summary(self, log_num: int = 0) -> None:
        """Open log link from list and navigate to all encounters summary."""
        self.driver.get(self.logs[log_num])

        logging.info(f"{datetime.now().time()}: Navigated to log.")

        time.sleep(0.5)

        fights_xp = ("/html/body/div[3]/div[2]/div[5]/div/div/div/div[2]/div/a[1]",  # noqa: E501
                     "/html/body/div[3]/div[2]/div[5]/div/div/div/div[2]/div/a[2]",  # noqa: E501
                     "/html/body/div[3]/div[2]/div[5]/div/div/div/div[2]/div/a[3]")  # noqa: E501

        logging.info(f"{datetime.now().time()}: Before search/ click.")

        self.driver.find_element(By.XPATH, fights_xp[self.enc_type]).click()

        logging.info(f"{datetime.now().time()}: After clicking.")

        # Some of the contents I want to parse take a few seconds to load.
        time.sleep(2)

    def get_comp(self) -> str:
        """Get html of summary page an return the composition table."""
        parsed_summary = BeautifulSoup(self.driver.page_source, "html.parser")
        comp_html = parsed_summary.find_all(class_="composition-entry")

        return str(comp_html)

    def check_comp(self, comp_html: str) -> tuple[str]:
        """Parse html string with regex and check/ update group composition.

        Args:
          comb_html: html string of the composition table.

        Raises:
          AttributeError: if comp is different to already existing comp.
        """
        comp = list(re.findall("\"[a-zA-Z]*\"", comp_html))
        comp = [s.strip('"') for s in comp]

        if len(self.comp) > 0 and sorted(self.comp) != sorted(tuple(comp)):
            self.quit()
            raise AttributeError(("Group comps in provided logs don't match."))
        else:
            self.comp = tuple(comp)

    def to_damage_dealt(self) -> None:
        """Navigate from "summary" to "damage dealt" tab."""
        sum_url = self.driver.current_url
        dd_url = (sum_url + "&type=damage-done")

        self.driver.get(dd_url)

    def get_damage_dealt(self) -> None:  # TODO
        """Create and return pandas dataframe made from html table."""
        dd_df = pd.DataFrame()

        parsed_damage = BeautifulSoup(self.driver.page_source, "html.parser")
        dd_html = parsed_damage.find(id="main-table-0")

        # print(dd_html.prettify)

        self.dd_dfs.append(dd_df)

    def to_healing_done(self) -> None:
        """Navigate from "damage dealt" to "healing" tab."""
        dd_url = self.driver.current_url
        hd_url = dd_url.replace("&type=damage-done", "&type=healing")

        self.driver.get(hd_url)

    def get_healing_done(self) -> None:  # TODO
        """Create and return pandas dataframe made from html table."""
        hd_df = pd.DataFrame()

        parsed_healing = BeautifulSoup(self.driver.page_source, "html.parser")
        hd_html = parsed_healing.find(id="main-table-0")

        # print(hd_html.prettify)

        self.hd_dfs.append(hd_df)

    def parse_logs(self) -> None:
        """Parse and scrape all given logs."""
        logging.info(f"{datetime.now().time()}: Before first_popup().")
        self.first_popup()
        logging.info(f"{datetime.now().time()}: After first_popup().")
        for log in range(len(self.logs)):
            logging.info(f"{datetime.now().time()}: Before to_summary().")
            self.to_summary(log)
            logging.info(f"{datetime.now().time()}: After to_summary().")
            self.check_comp(self.get_comp())
            self.to_damage_dealt()
            self.get_damage_dealt()
            self.to_healing_done()
            self.get_healing_done()
        self.quit()
