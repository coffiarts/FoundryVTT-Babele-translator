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

        self.current_response_queue = None

        self.question_label = ctk.CTkLabel(
            self,
            text=""
        )
        self.question_label.pack(padx=20, pady=(10, 5), anchor="w")

        self.answer_entry = ctk.CTkEntry(
            self,
            width=400
        )
        self.answer_entry.pack(padx=20, pady=5, fill="x")

        self.submit_button = ctk.CTkButton(
            self,
            text="OK",
            command=self.submit_answer
        )
        self.submit_button.pack(padx=20, pady=(0, 20))

        # zunächst unsichtbar
        self.question_label.pack_forget()
        self.answer_entry.pack_forget()
        self.submit_button.pack_forget()

        self.check_dialog_requests()

        self.LOGGER = self.log_message

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

            self.current_response_queue = response_queue

            self.question_label.configure(text=question)

            self.question_label.pack(
                padx=20,
                pady=(10, 5),
                anchor="w"
            )

            self.answer_entry.pack(
                padx=20,
                pady=5,
                fill="x"
            )

            self.submit_button.pack(
                padx=20,
                pady=(0, 20)
            )

            self.answer_entry.focus()

        self.after(50, self.check_dialog_requests)


    def log_message(self, message):
        self.log.insert("end", message + "\n")
        self.log.see("end")


    def translation_finished(self):
        self.after(
            0,
            lambda: self.start_button.configure(state="normal")
        )


    def submit_answer(self):

        if self.current_response_queue is None:
            return

        answer = self.answer_entry.get().strip().upper()

        self.current_response_queue.put(answer)

        self.answer_entry.delete(0, "end")

        self.question_label.pack_forget()
        self.answer_entry.pack_forget()
        self.submit_button.pack_forget()

        self.current_response_queue = None


app = App()
app.mainloop()