#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 3 of the License,
    or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
    See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, see <http://www.gnu.org/licenses/>.

    @author: RaNaN
"""
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import os
import sys
from getpass import getpass
from subprocess import (
    PIPE,
    call,
)
from sys import exit

from six.moves import input

import module.common.pylgettext as gettext
from module.util.compatibility import (
    IS_WINDOWS,
    install_translation,
)
from module.util.encoding import smart_text
from module.utils import get_console_encoding


class Setup():
    """
    pyLoads initial setup configuration assistent
    """

    def __init__(self, path, config):
        self.path = path
        self.config = config
        self.stdin_encoding = get_console_encoding(sys.stdin.encoding)

    def start(self):
        langs = self.config.getMetaData("general", "language")["type"].split(";")
        lang = self.ask("Choose your Language / Wähle deine Sprache", "en", langs)
        gettext.setpaths([os.path.join(os.sep, "usr", "share", "pyload", "locale"), None])
        translation = gettext.translation(
            "setup",
            os.path.join(self.path, "locale"),
            languages=[lang, "en"],
            fallback=True,
        )
        install_translation(translation)

        #Input shorthand for yes
        self.yes = _("y")
        #Input shorthand for no
        self.no = _("n")

        #        print ""
        #        print _("Would you like to configure pyLoad via Webinterface?")
        #        print _("You need a Browser and a connection to this PC for it.")
        #        viaweb = self.ask(_("Start initial webinterface for configuration?"), "y", bool=True)
        #        if viaweb:
        #            try:
        #                from module.web import ServerThread
        #                ServerThread.setup = self
        #                from module.web import webinterface
        #                webinterface.run_simple()
        #                return False
        #            except Exception, e:
        #                print "Setup failed with this error: ", e
        #                print "Falling back to commandline setup."


        print("")
        print(_("Welcome to the pyLoad Configuration Assistent."))
        print(_("It will check your system and make a basic setup in order to run pyLoad."))
        print("")
        print(_("The value in brackets [] always is the default value,"))
        print(_("in case you don't want to change it or you are unsure what to choose, just hit enter."))
        print(_(
            "Don't forget: You can always rerun this assistent with --setup or -s parameter, when you start pyLoadCore."))
        print(_("If you have any problems with this assistent hit STRG-C,"))
        print(_("to abort and don't let him start with pyLoadCore automatically anymore."))
        print("")
        print(_("When you are ready for system check, hit enter."))
        input()

        basic, ssl, captcha, web, js = self.system_check()
        print("")

        if not basic:
            print(_("You need pycurl, sqlite and Python 2.7 or newer to run pyLoad."))
            print(_("Please correct this and re-run pyLoad."))
            print(_("Setup will now close."))
            input()
            return False

        input(_("System check finished, hit enter to see your status report."))
        print("")
        print(_("## Status ##"))
        print("")

        avail = []
        if self.check_module("Cryptodome"): avail.append(_("container decrypting"))
        if ssl: avail.append(_("ssl connection"))
        if captcha: avail.append(_("automatic captcha decryption"))
        if web: avail.append(_("Webinterface"))
        if js: avail.append(_("extended Click'N'Load"))

        string = ""

        for av in avail:
            string += ", " + av

        print(_("Features available:") + string[1:])
        print("")

        if len(avail) < 5:
            print(_("Featues missing: "))
            print("")

            if not self.check_module("Cryptodome"):
                print(_("** no py-crypto available **"))
                print(_("You need this if you want to decrypt container files."))
                print("")

            if not ssl:
                print(_("** no SSL available **"))
                print(_("This is needed if you want to establish a secure connection to core or webinterface."))
                print(_("If you only want to access locally to pyLoad ssl is not usefull."))
                print("")

            if not captcha:
                print(_("** no Captcha OCR Recognition available **"))
                print(_("Only needed for some hosters and as freeuser."))
                print("")

            if not js:
                print(_("** no JavaScript engine found **"))
                print(_("You will need this for some Click'N'Load links. Install Spidermonkey, ossp-js, pyv8 or rhino"))

            print(_("You can abort the setup now and fix some dependicies if you want."))

        con = self.ask(_("Continue with setup?"), self.yes, bool=True)

        if not con:
            return False

        print("")
        print(_("Do you want to change the config path? Current is %s") % os.path.abspath(""))
        print(_(
            "If you use pyLoad on a server or the home partition lives on an internal flash it may be a good idea to change it."))
        path = self.ask(_("Change config path?"), self.no, bool=True)
        if path:
            self.conf_path()
            #calls exit when changed

        print("")
        print(_("Do you want to configure login data and basic settings?"))
        print(_("This is recommend for first run."))
        con = self.ask(_("Make basic setup?"), self.yes, bool=True)

        if con:
            self.conf_basic()

        if ssl:
            print("")
            print(_("Do you want to configure ssl?"))
            ssl = self.ask(_("Configure ssl?"), self.no, bool=True)
            if ssl:
                self.conf_ssl()

        if web:
            print("")
            print(_("Do you want to configure webinterface?"))
            web = self.ask(_("Configure webinterface?"), self.yes, bool=True)
            if web:
                self.conf_web()

        print("")
        print(_("Setup finished successfully."))
        print(_("Hit enter to exit and restart pyLoad"))
        input()
        return True

    def system_check(self):
        """ make a systemcheck and return the results"""
        print(_("## System Check ##"))

        if sys.version_info[:2] < (2, 7):
            print(_("Your Python version is too old. Please use at least Python 2.7"))
            python = False
        else:
            print(_("Python Version: OK"))
            python = True

        curl = self.check_module("pycurl")
        self.print_dep("pycurl", curl)

        sqlite = self.check_module("sqlite3")
        self.print_dep("sqlite3", sqlite)

        basic = python and curl and sqlite

        print("")

        crypto = self.check_module("Cryptodome")
        self.print_dep("pycryptodome", crypto)

        ssl = self.check_module("OpenSSL")
        self.print_dep("py-OpenSSL", ssl)

        print("")

        pil = self.check_module("Image") or self.check_module("PIL")
        self.print_dep("py-imaging", pil)

        if IS_WINDOWS:
            tesser = self.check_prog([os.path.join(pypath, "tesseract", "tesseract.exe"), "-v"])
        else:
            tesser = self.check_prog(["tesseract", "-v"])

        self.print_dep("tesseract", tesser)

        captcha = pil and tesser

        print("")

        jinja = True

        try:
            import jinja2

            v = jinja2.__version__
            if v and "unknown" not in v:
                jinja2_version = tuple(int(value) for value in v.split('.'))
                if jinja2_version < (2, 6):
                    print(_("Your installed jinja2 version %s seems too old.") % jinja2.__version__)
                    print(_("You can safely continue but if the webinterface is not working,"))
                    print(_("please upgrade or deinstall it, pyLoad includes a sufficient jinja2 libary."))
                    print("")
                    jinja = False
        except:
            pass

        self.print_dep("jinja2", jinja)
        beaker = self.check_module("beaker")
        self.print_dep("beaker", beaker)

        web = sqlite and beaker

        from module.common import JsEngine

        js = True if JsEngine.ENGINE else False
        self.print_dep(_("JS engine"), js)

        return basic, ssl, captcha, web, js

    def conf_basic(self):
        print("")
        print(_("## Basic Setup ##"))

        print("")
        print(_("The following logindata is valid for CLI and webinterface."))

        from module.database import DatabaseBackend

        db = DatabaseBackend(None)
        db.setup()
        username = self.ask(_("Username"), "User")
        password = self.ask("", "", password=True)
        db.addUser(username, password)
        db.shutdown()

        print("")
        print(_("External clients (CLI or other) need remote access to work over the network."))
        print(_("However, if you only want to use the webinterface you may disable it to save ram."))
        self.config["remote"]["activated"] = self.ask(_("Enable remote access"), self.yes, bool=True)

        print("")
        langs = self.config.getMetaData("general", "language")
        self.config["general"]["language"] = self.ask(_("Language"), "en", langs["type"].split(";"))

        self.config["general"]["download_folder"] = self.ask(_("Downloadfolder"), "Downloads")
        self.config["download"]["max_downloads"] = self.ask(_("Max parallel downloads"), "3")
        #print _("You should disable checksum proofing, if you have low hardware requirements.")
        #self.config["general"]["checksum"] = self.ask(_("Proof checksum?"), "y", bool=True)

        reconnect = self.ask(_("Use Reconnect?"), self.no, bool=True)
        self.config["reconnect"]["activated"] = reconnect
        if reconnect:
            self.config["reconnect"]["method"] = self.ask(_("Reconnect script location"), "./reconnect.sh")


    def conf_web(self):
        print("")
        print(_("## Webinterface Setup ##"))

        print("")
        self.config["webinterface"]["activated"] = self.ask(_("Activate webinterface?"), self.yes, bool=True)
        print("")
        print(_("Listen address, if you use 127.0.0.1 or localhost, the webinterface will only accessible locally."))
        self.config["webinterface"]["host"] = self.ask(_("Address"), "0.0.0.0")
        self.config["webinterface"]["port"] = self.ask(_("Port"), "8000")
        print("")
        print(_("pyLoad offers several server backends, now following a short explanation."))
        print("builtin:", _("Default server, best choice if you dont know which one to choose."))
        print("threaded:", _("This server offers SSL and is a good alternative to builtin."))
        print("fastcgi:", _(
            "Can be used by apache, lighttpd, requires you to configure them, which is not too easy job."))
        print("lightweight:", _("Very fast alternative written in C, requires libev and linux knowlegde."))
        print("\t", _("Get it from here: https://github.com/jonashaag/bjoern, compile it"))
        print("\t", _("and copy bjoern.so to module/lib"))

        print("")
        print(_(
            "Attention: In some rare cases the builtin server is not working, if you notice problems with the webinterface"))
        print(_("come back here and change the builtin server to the threaded one here."))

        self.config["webinterface"]["server"] = self.ask(_("Server"), "builtin",
            ["builtin", "threaded", "fastcgi", "lightweight"])

        print("")
        print(_("pyLoad offers several web user interface templates, please choose a webinterface template you like."))

        templates = [t for t in os.listdir(os.path.join(pypath, "module", "web", "templates"))
                     if os.path.isdir(os.path.join(pypath, "module", "web", "templates", t))]
        self.config["webinterface"]["template"] = self.ask(_("Template"), "classic", templates)

    def conf_ssl(self):
        print("")
        print(_("## SSL Setup ##"))
        print("")
        print(_("Execute these commands from pyLoad config folder to make ssl certificates:"))
        print("")
        print("openssl genrsa -out ssl.key 1024")
        print("openssl req -new -key ssl.key -out ssl.csr")
        print("openssl req -days 36500 -x509 -key ssl.key -in ssl.csr > ssl.crt ")
        print("")
        print(_("If you're done and everything went fine, you can activate ssl now."))

        ssl = self.ask(_("Activate SSL?"), self.yes, bool=True)
        self.config["ssl"]["activated"] = ssl
        self.config["webinterface"]["https"] = ssl

    def set_user(self):
        gettext.setpaths([os.path.join(os.sep, "usr", "share", "pyload", "locale"), None])
        translation = gettext.translation(
            "setup",
            os.path.join(self.path, "locale"),
            languages=[self.config["general"]["language"], "en"],
            fallback=True,
        )
        install_translation(translation)

        from module.database import DatabaseBackend

        db = DatabaseBackend(None)
        db.setup()

        noaction = True
        try:
            while True:
                print(_("Select action"))
                print(_("1 - Create/Edit user"))
                print(_("2 - List users"))
                print(_("3 - Remove user"))
                print(_("4 - Quit"))
                action = input("[1]/2/3/4: ")
                if not action in ("1", "2", "3", "4"):
                    continue
                elif action == "1":
                    print("")
                    username = self.ask(_("Username"), "User")
                    password = self.ask("", "", password=True)
                    db.addUser(username, password)
                    noaction = False
                elif action == "2":
                    print("")
                    print(_("Users"))
                    print("-----")
                    users = db.listUsers()
                    noaction = False
                    for user in users:
                        print(user)
                    print("-----")
                    print("")
                elif action == "3":
                    print("")
                    username = self.ask(_("Username"), "")
                    if username:
                        db.removeUser(username)
                        noaction = False
                elif action == "4":
                    break
        finally:
            if not noaction:
                db.shutdown()

    def conf_path(self, trans=False):
        if trans:
            gettext.setpaths([os.path.join(os.sep, "usr", "share", "pyload", "locale"), None])
            translation = gettext.translation(
                "setup",
                os.path.join(self.path, "locale"),
                languages=[self.config["general"]["language"], "en"],
                fallback=True,
            )
            install_translation(translation)

        print(_("Setting new configpath, current configuration will not be transfered!"))
        path = self.ask(_("Configpath"), os.path.abspath(""))
        try:
            path = os.path.join(pypath, path)
            if not os.path.exists(path):
                os.makedirs(path)
            f = open(os.path.join(pypath, "module", "config", "configdir"), "wb")
            f.write(path)
            f.close()
            print(_("Configpath changed, setup will now close, please restart to go on."))
            print(_("Press Enter to exit."))
            input()
            exit()
        except Exception as e:
            print(_("Setting config path failed: %s") % str(e))

    def print_dep(self, name, value):
        """Print Status of dependency"""
        if value:
            print(_("%s: OK") % name)
        else:
            print(_("%s: missing") % name)


    def check_module(self, module):
        try:
            __import__(module)
            return True
        except:
            return False

    def check_prog(self, command):
        pipe = PIPE
        try:
            call(command, stdout=pipe, stderr=pipe)
            return True
        except:
            return False

    def ask(self, qst, default, answers=[], bool=False, password=False):
        """produce one line to asking for input"""
        if answers:
            info = "("

            for i, answer in enumerate(answers):
                info += (", " if i != 0 else "") + str((answer == default and "[%s]" % answer) or answer)

            info += ")"
        elif bool:
            if default == self.yes:
                info = "([%s]/%s)" % (self.yes, self.no)
            else:
                info = "(%s/[%s])" % (self.yes, self.no)
        else:
            info = "[%s]" % default

        if password:
            p1 = True
            p2 = False
            while p1 != p2:
                # getpass(_("Password: ")) will crash on systems with broken locales (Win, NAS)
                sys.stdout.write(_("Password: "))
                p1 = getpass("")

                if len(p1) < 4:
                    print(_("Password too short. Use at least 4 symbols."))
                    continue

                sys.stdout.write(_("Password (again): "))
                p2 = getpass("")

                if p1 == p2:
                    return p1
                else:
                    print(_("Passwords did not match."))

        while True:
            try:
                input_value = input(qst + " %s: " % info)
            except KeyboardInterrupt:
                print("\nSetup interrupted")
                exit()

            input_value = smart_text(input_value, encoding=self.stdin_encoding)

            if input_value.strip() == "":
                input_value = default

            if bool:
                # yes, true,t are inputs for booleans with value true
                if input_value.lower().strip() in [self.yes, _("yes"), _("true"), _("t"), "yes"]:
                    return True
                # no, false,f are inputs for booleans with value false
                elif input_value.lower().strip() in [self.no, _("no"), _("false"), _("f"), "no"]:
                    return False
                else:
                    print(_("Invalid Input"))
                    continue

            if not answers:
                return input_value

            if input_value in answers:
                return input_value

            print(_("Invalid Input"))


if __name__ == "__main__":
    test = Setup(os.path.join(os.path.abspath(os.path.dirname(__file__)), ".."), None)
    test.start()
