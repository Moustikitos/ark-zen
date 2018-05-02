# -*- coding:utf-8 -*-

from zen import tfa, HOME
from zen import crypto
from tkinter import ttk

import io
import os
import sys
import time
import tkinter
import threading

# ROOT = os.path.abspath(os.path.dirname(__file__))

# create and configure main frame
main = ttk.Frame()
main.pack(fill="both", expand=True)
main.columnconfigure(0, weight=1)
main.rowconfigure(1, weight=1)
app = main.winfo_toplevel()
app.title("TFA tool")
app.resizable(False, False)
style = ttk.Style()


############
## BANNER ##
############

# create and configure banner
style.configure("pannel.TFrame", background="steelblue")
banner = ttk.Frame(main, height=75, padding=4, style="pannel.TFrame")
banner.grid(row=0, column=0, sticky="nesw")


#############
## CONTENT ##
#############

# create and configure content
style.configure("content.TFrame")
content = ttk.Frame(main, padding=0, style="content.TFrame")
content.grid(row=1, column=0, sticky="nesw")
content.columnconfigure(1, weight=1, minsize=70)
content.columnconfigure(3, weight=1, minsize=70)

ttk.Label(content, text="Signature").grid(row=0, column=0, padx=4, pady=4)
combo = ttk.Combobox(content, width=0, state="readonly")
combo.grid(row=0, column=1, sticky="ew", padx=4, pady=4)
ttk.Label(content, text="Pin").grid(row=0, column=2, padx=4, pady=4)
ttk.Entry(content, width=0, textvariable="pin_code", justify="center", show="-").grid(sticky="ew", row=0, column=3, padx=4, pady=4)

add = ttk.Button(content, text="Add", style="Toolbutton")
add.grid(row=0, column=4, sticky="w", padx=0, pady=4)

remove = ttk.Button(content, text="Remove", style="Toolbutton")
remove.grid(row=0, column=5, sticky="e", padx=4, pady=4)


############
## FOOTER ##
############

# create and configure footer
ttk.Separator(main, orien="horizontal").grid(row=2, column=0, sticky="nesw")
style.configure("footer.TFrame", background="white")
style.configure("footer.TButton", background=style.lookup("footer.TFrame", "background"), font=("tahoma", 8, "bold"))
footer = ttk.Frame(main, padding=4, style="footer.TFrame")
footer.grid(row=3, column=0, sticky="nesw")

style.configure("footer.Horizontal.TProgressbar", background=style.lookup("footer.TFrame", "background"))
progress = ttk.Progressbar(footer, variable="progress_value", style="footer.Horizontal.TProgressbar")
progress.pack(side="left", fill="x", padx=4, pady=8)

copy = ttk.Button(footer, width=-1, default="active", padding=(10,0), text="Copy TFA to clipboard", style="footer.TButton")
copy.pack(side="right", fill="y", padx=4, pady=4)


###########
## ADDER ##
###########

# create and configure adder
style.configure("adder.TFrame", background="steelblue")
style.configure("adder.TLabel", background=style.lookup("adder.TFrame", "background"))
style.configure("adder.TButton", background=style.lookup("adder.TFrame", "background"))
adder = ttk.Frame(main, padding=(8,8,8,0), style="adder.TFrame")
adder.columnconfigure(1, weight=1)
adder.rowconfigure(2, weight=1)

ttk.Label(adder, text="Name", padding=(0,0,4), style="adder.TLabel").grid(row=0, column=0, padx=0, pady=0, sticky="nw")
name = tkinter.Entry(adder, textvariable="signature_name")
name.grid(row=0, column=1, columnspan=2, padx=0, pady=0, sticky="nesw")

ttk.Label(adder, text="Pin code", padding=(0,0,4), style="adder.TLabel").grid(row=1, column=0, padx=0, pady=8, sticky="nw")
pin = tkinter.Entry(adder, textvariable="pin_code", show="-")
pin.grid(row=1, column=1, columnspan=2, padx=0, pady=8, sticky="nesw")

ttk.Label(adder, text="Passphrase", padding=(0,0,4), style="adder.TLabel").grid(row=2, column=0, padx=0, pady=0, sticky="nw")
passphrase = tkinter.Text(adder, font=("tahoma", 8, "bold"))
passphrase.grid(row=2, column=1, columnspan=2, padx=0, pady=0, sticky="nesw")

esc = ttk.Button(adder, width=-1, paddin=(4,0), text="Cancel", style="adder.TButton")
esc.grid(row=3, column=1, sticky="nes", padx=8, pady=8)

ok = ttk.Button(adder, width=-1, paddin=(4,0), default="active", text="Ok", style="adder.TButton")
ok.grid(row=3, column=2, sticky="ns", padx=0, pady=8)
ok.state(("disabled",))


###############
## CALLBACKS ##
###############

signature_check = lambda a=app,p=passphrase: a.getvar("signature_name") != "" and p.get("1.0", "1.end") != "" and a.getvar("pin_code") != ""

update_ok = lambda e,obk=ok: ok.state(("!disabled",) if signature_check() else ("disabled",))

def update_signatures():
	folder = os.path.join(HOME, ".sign")
	combo["values"] = () if not os.path.exists(folder) else \
	                  tuple(filter(lambda e:os.path.exists(os.path.join(folder, e)), os.listdir(folder)))

def add_signature():
	sign_name = app.getvar("signature_name")
	if sign_name != "":
		base = crypto.createBase(app.getvar("pin_code"))
		keys = crypto.getKeys(passphrase.get("1.0","1.end").strip())
		crypto.dumpAccount(base, keys["publicKey"], keys["privateKey"], None, sign_name)
		esc.invoke()
	else:
		pass
	update_signatures()

def remove_signature():
	fullpath = os.path.join(os.path.join(HOME, ".sign"), combo.get())
	if os.path.isfile(fullpath):
		os.remove(fullpath)
	update_signatures()
	combo.set("")
	app.setvar("signature_name", "")
	app.setvar("pin_code", "")

def update_progress():
	while True:
		time.sleep(0.25)
		value = time.time() % 60 / 60
		copy.state(("disabled",) if value > 56./60 or \
			                        value < 2./60 or \
			                        app.getvar("pin_code") == "" or \
			                        combo.get() == "" \
			                     else ("!disabled",))
		app.setvar("progress_value", value * 100)

def get_signature():
	app.clipboard_clear()
	try:
		base = crypto.createBase(app.getvar("pin_code"))
		keys = crypto.loadAccount(base, combo.get())
		print(keys)
		data = crypto.hexlify(tfa.get(keys["privateKey"]))
	except Exception as e:
		app.clipboard_append("Error occur: %r"%e)
	else:
		app.clipboard_append(data)

#################
## LINKS/BINDS ##
#################

# connect button to callback
ok["command"] = add_signature
add["command"] = lambda f=adder: f.place(x=0, y=0, relwidth=1.0, relheight=1.0, anchor="nw")
esc["command"] = lambda app=app,obj=adder,txt=passphrase: [
	obj.place_forget(),
	txt.delete("1.0", "end"),
	app.setvar("signature_name", ""),
]
copy["command"] = get_signature
remove["command"] = remove_signature
# bind events
pin.bind("<FocusOut>", update_ok)
name.bind("<FocusOut>", update_ok)
passphrase.bind("<FocusOut>", update_ok)

update_signatures()

############
## LAUNCH ##
############
# update progressvar value and launch thread 
app.setvar("progress_value", time.time() % 60 / 60 * 100)
thread = threading.Thread(target=update_progress, args=())
thread.daemon = True
thread.start()

# launch app
app.mainloop()
