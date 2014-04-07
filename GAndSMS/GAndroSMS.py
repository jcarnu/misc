#!/usr/bin/python
# -*- coding: utf-8 -*-
import gi, os, time,sqlite3
gi.require_version("Gtk","3.0")
from gi.repository import Gtk,GdkPixbuf,GObject,Pango,Gdk

class GAndroSMS:
	def __init__(self):
		GObject.threads_init()
		
		#On crée l'accès à la base
		#On peut la créer directement :
		#create table contact2(id integer primary key autoincrement, nom text not null,  phone text not null);
		self.engine = sqlite3.connect('GAndroSMS.db')
		self.curs = self.engine.cursor()
	    
	    # On charge l'IHM
		self.interface = Gtk.Builder()
		self.interface.add_from_file('GAndroSMS.glade')
		
		#Conteneur des contacts (M du MVC)
		self.contactstore  = self.interface.get_object("lstContacts")
		# Contenu du SMS
		self.edit = self.interface.get_object("textview1")
		# Liste des contacts
		self.tree = self.interface.get_object("treeview1")
		
		# On détruit le conteneur existant et on charge à partir de la DB
		self.contactstore.clear()
		for ctc in self.curs.execute("SELECT nom,phone,id from contact ORDER BY nom"):
			self.contactstore.append(ctc)
			#contact.append(ctc)
		
		# On crée les renderer de colonnes
		column = Gtk.TreeViewColumn('Contact', Gtk.CellRendererText(), text=0)   
		column.set_clickable(True)   
		column.set_resizable(True)   
		self.tree.append_column(column)

		column = Gtk.TreeViewColumn('N°', Gtk.CellRendererText(), text=1)   
		column.set_clickable(True)   
		column.set_resizable(True)   
		self.tree.append_column(column)

		# Signaux
		self.interface.connect_signals(self)
		#Dialogue de saisie/modification d'une entrée
		self.dial = self.interface.get_object('dialog1')
		self.nom = self.interface.get_object('entrynom')
		self.phone = self.interface.get_object('entryphone')
		# Création ou edition
		self.editing = False
		self.window = self.interface.get_object("window1")
		self.window.connect("delete-event", self.on_mainWindow_destroy)
		self.window.show_all()

	def on_mainWindow_destroy(self, widget,arg=None):
		"""Fin de l'application"""
		if self.engine:
			self.curs.close()
			self.engine.close()
			print "Base sauvegardee"
		Gtk.main_quit()
		
	def onSendClick(self,widget):
		"""Envoi du SMS avec ADB shell et activity manager"""
		print "Send"
		txt = self.edit.get_buffer()
		texte = txt.get_text(txt.get_start_iter(),txt.get_end_iter(),False)
		texte = texte.replace("\"","\\\"").replace("\n","\r\n")
		model,treeiter = self.tree.get_selection().get_selected()
		print texte
		# Récupération des données et transformation des LF en CRLF
		tel = model[treeiter][1].replace("\n","\r\n")
		qui = model[treeiter][0]
		print "To ",qui," (",tel,")"
		adb_seq=[' am start -a android.intent.action.SENDTO -d "sms:%s" --es sms_body "%s" --ez exit_on_sent true'%(tel,texte),
				 '  input keyevent 22',' input keyevent 66']
		for shellcmd in adb_seq:
			os.system("adb shell %s"%shellcmd)
			print "adb shell %s"%shellcmd
			time.sleep(1) # Ne pas aller trop vite on simule les touches.
		
	def onAddButton(self,widget):		
		"""On affiche un dialogue permettant la saisie"""
		response = self.dial.run()
		
	def onEditButton(self,widget):
		"""On affiche un dialogue de saisie déjà prérempli avec les données de l'élément concerné"""
		model,treeiter = self.tree.get_selection().get_selected()
		tel = model[treeiter][1]
		qui = model[treeiter][0]
		self.currentid = model[treeiter][2]
		self.nom.set_text(qui)
		self.phone.set_text(tel)
		self.editing = True
		response = self.dial.run()
		
	def onCancelAdd(self,widget):
		"""On abandonne la saisie/modification"""
		self.dial.hide()
		
	def onAddItem(self,widget):
		"""Add or edit contact entry"""
		if self.editing:
			query = 'UPDATE contact SET nom="{0}",phone="{1}" WHERE id="{2}"'.format(self.nom.get_text(),self.phone.get_text(),self.currentid)
		else:
			query = 'INSERT INTO contact(nom,phone) VALUES ("{0}","{1}")'.format(self.nom.get_text(),self.phone.get_text())
		print query
		self.curs.execute(query)
		self.engine.commit()
		if not self.editing:
			self.curs.execute('SELECT id FROM contact WHERE nom="{0}" AND phone="{1}"'.format(self.nom.get_text(),self.phone.get_text()))
			self.currentid = self.curs.fetchone()[0]
			self.contactstore.append([self.nom.get_text(),self.phone.get_text(),self.currentid])
		else:
			model,treeiter = self.tree.get_selection().get_selected()
			model[treeiter][1]=self.phone.get_text()
			model[treeiter][0]=self.nom.get_text()
		self.currentid=-1
		self.editing=False;
		self.dial.hide()
		
	def onDeleteItem(self,widget):
		"""Delete contact entry"""
		model,treeiter = self.tree.get_selection().get_selected()
		phone = model[treeiter][1]
		nom = model[treeiter][0]
		id_ = model[treeiter][2]
		dialog = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.QUESTION, Gtk.ButtonsType.YES_NO, "Etes vous sûr de vouloir supprimer l'enregisrement suivant ?")
		dialog.format_secondary_text("Contact %s (%s)."%(nom,phone))
		response = dialog.run()
		if response == Gtk.ResponseType.YES:
			print("QUESTION dialog closed by clicking YES button")
			#Checker si ok/Ko
			query = 'DELETE FROM contact WHERE id = "{0}"'.format(id_)
			print query
			self.curs.execute(query)
			self.contactstore.remove(treeiter)
			self.engine.commit()
		elif response == Gtk.ResponseType.NO:
			print("QUESTION dialog closed by clicking NO button")
		dialog.destroy()
	
	def initContactList(self, widget):
		pass
		
	def onQuitClick(self,widget):
		"""On quitte l'application"""
		if self.engine:
			print "cloture de la base"
			self.curs.close()
			self.engine.close()
			print "ok"
		Gtk.main_quit()
	def on_window_destroy(self, widget, data=None):
		"""L'application se ferme"""
		if self.engine:
			self.curs.close()
			self.engine.close()
        Gtk.main_quit()

if __name__ == "__main__":
	"""Basique"""
	GAndroSMS()
	Gtk.main()
