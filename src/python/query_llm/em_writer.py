import json
import os

class EMwriter:
    def __init__(self, rminer_datafile, dest_dir):
        self.dest_dir = dest_dir
        self.rminer_datafile = rminer_datafile

    def write(self, em_metadata, dest_file):
        try:
            os.makedirs(self.dest_dir)
        except FileExistsError:
            pass
        with open(dest_file, "w") as f:
            json.dump(em_metadata, f, indent=1)

    def read(self, function_details):
        pass

    def getdata(self):
        with open(self.rminer_datafile) as f:
            self.rminer_data = json.load(f)
        return self.rminer_data

    def get_filename(self, em_data):
        return em_data['filename']

    def get_projectname(self, em_data):
        return em_data['projectName']

    def get_commitafter(self, em_data):
        return em_data['sha']

    def get_func_str(self, em_data, file_str):
        start_offset = em_data['host_start_off_set']
        end_offset = em_data['host_end_off_set']
        func_str = file_str[start_offset:end_offset]
        return func_str

    def get_startline(self, em_data):
        return em_data['host_start_line']

    def get_endline(self, em_data):
        return em_data['host_end_line']

    def exists(self, dest_file):
        return os.path.exists(dest_file)


