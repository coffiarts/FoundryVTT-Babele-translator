import queue
import customtkinter as ctk
import dialogs
import threading
import translate

class App(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Foundry VTT Translator")

        self.button = ctk.CTkButton(
            self,
            text="Start",
            command=self.start_translation
        )
        self.button.pack(padx=20, pady=20)

        self.log = ctk.CTkTextbox(self, width=600, height=300)
        self.log.pack(padx=20, pady=20, fill="both", expand=True)

        self.check_dialog_requests()

    def start_translation(self):
        threading.Thread(
            target=translate.run_translation,
            daemon=True,
            kwargs={
                "logger": self.log_message
            }
        ).start()

    def check_dialog_requests(self):
        try:
            question, response_queue = dialogs.get_request()

        except queue.Empty:
            pass

        else:
            answer = ctk.CTkInputDialog(
                text=question,
                title="Translation"
            ).get_input().strip().upper()

            response_queue.put(answer)

        self.after(50, self.check_dialog_requests)

    def log_message(self, message):
        self.log.insert("end", message + "\n")
        self.log.see("end")

app = App()
app.mainloop()