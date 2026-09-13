import queue
import customtkinter as ctk
import dialogs
import threading
import translate

class App(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Foundry VTT Translator")

        self.start_button = ctk.CTkButton(
            self,
            text="Start",
            command=self.start_translation
        )
        self.start_button.pack(padx=20, pady=20)

        self.log = ctk.CTkTextbox(self, width=600, height=300)
        self.log.pack(padx=20, pady=20, fill="both", expand=True)

        self.check_dialog_requests()

    def start_translation(self):
        self.start_button.configure(state="disabled")

        threading.Thread(
            target=translate.run_translation,
            kwargs={
                # deine normalen Parameter ...
                "logger": self.log_message,
                "finished": self.translation_finished,
            },
            daemon=True
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


    def translation_finished(self):
        self.after(
            0,
            lambda: self.start_button.configure(state="normal")
        )

app = App()
app.mainloop()