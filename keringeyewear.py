def manage_thread_list(self, length):
    while len(self.thread_list) < length:
        for obj in self.thread_list:
            if obj.status == "completed":
                self.thread_list.remove(obj)
                break
        sleep(1)