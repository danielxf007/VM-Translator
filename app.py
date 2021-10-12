import json, os, glob


class Translator:

    def __init__(self, asm_translations):
        self.asm_translations = asm_translations
        self.comment_format = "// {arg0} {arg1} {arg2}"
        self.labels_index = {"eq":0, "lt":0, "gt":0, "if-goto":0, "call":0}
    
    def translate(self, files_content):
        self.labels_index = {"eq":0, "lt":0, "gt":0, "if-goto":0, "call":0}
        translation = self.get_bootstrap()
        for file_content in files_content:
            file_name = file_content["file_name"]
            commands = file_content["commands"]
            for command in commands:
                arg0 = command["arg0"]
                arg1 = command["arg1"]
                arg2 = command["arg2"]
                translation+=[self.comment_format.format(arg0 = arg0, arg1 = arg1 if arg1 else "", arg2 = arg2 if arg2 else "")]
                if arg0 == "push":
                    translation+=self.translate_push(arg0, arg1, arg2, file_name)
                elif arg0 == "pop":
                    translation+=self.translate_pop(arg0, arg1, arg2, file_name)
                elif arg0 == "eq" or arg0 == "gt" or arg0 == "lt":
                    translation+=self.translate_bool_command(arg0)
                elif arg0 == "label":
                    translation+=self.translate_label(arg0, arg1)
                elif arg0 == "goto":
                    translation+=self.translate_goto(arg0, arg1)
                elif arg0 == "if-goto":
                    translation+=self.translate_if_goto(arg0, arg1)
                elif arg0 == "call":
                    translation+=self.translate_call(arg0, arg1, arg2)
                elif arg0 == "function":
                    translation+=self.translate_func(arg0, arg1, arg2)
                elif arg0 == "return":
                    translation+=self.translate_ret(arg0)
                else:
                    translation+=self.asm_translations[arg0]
        return translation
    
    def get_bootstrap(self):
        return self.asm_translations["bootstrap"] + self.translate_call("call", "Sys.init", "0")

    def translate_push(self, command, segment, index, file_name):
        push_transl = self.asm_translations[command]
        if(segment == "static"):
            translation = ["\n".join(push_transl[segment]).format(file_name = file_name, index = index)]
        elif(segment == "pointer"):
            translation = push_transl[segment][index]
        else:
            translation = ["\n".join(push_transl[segment]).format(index = index)]
        translation+=push_transl["add_to_sp"]
        translation+=push_transl["inc_sp"]
        return translation
    
    def translate_pop(self, command, segment, index, file_name):
        pop_transl = self.asm_translations[command]
        if(segment == "static"):
            return ["\n".join(pop_transl[segment]).format(file_name = file_name, index = index)]
        elif(segment == "pointer"):
            return pop_transl[segment][index]
        translation = ["\n".join(pop_transl[segment]).format(index = index)]
        translation+=pop_transl["add_to_segment"]
        translation+=pop_transl["dec_sp"]
        return translation
    
    def translate_bool_command(self, command):
        translation = ["\n".join(self.asm_translations[command]).format(index = self.labels_index[command])]
        self.labels_index[command]+=1
        return self.asm_translations["sub"] + translation
    
    def translate_label(self, command, label):
        return [self.asm_translations[command].format(label = label)]
    
    def translate_goto(self, command, label):
        return ["\n".join(self.asm_translations[command]).format(label = label)]

    def translate_if_goto(self, command, label):
        translation = ["\n".join(self.asm_translations[command]).format(label = label, index = self.labels_index[command])]
        self.labels_index[command]+=1
        return translation

    def translate_call(self, command, label, index):
        translation_steps = self.asm_translations[command]
        translation = ["\n".join(translation_steps["save_ret_addr"]).format(n_call = self.labels_index[command])]
        translation+=translation_steps["save_segments"]
        translation+=["\n".join(translation_steps["set_arg"]).format(index = index)]
        translation+=translation_steps["set_lcl"]
        translation+=["\n".join(translation_steps["transfer_control"]).format(label = label, n_call = self.labels_index[command])]
        self.labels_index[command]+=1
        return translation
    
    def translate_func(self, command, label, index):
        func_transl = self.asm_translations[command]
        translation = ["\n".join(func_transl["set_local"]).format(label = label)]
        if index != "0":
            translation+=func_transl["set_D_zero"]
            for _i in range(int(index)):
                translation+=func_transl["add_to_sp"]
                translation+=func_transl["inc_sp"]
        return translation
    
    def translate_ret(self, command):
        translation = []
        for key in self.asm_translations[command]:
            translation+=self.asm_translations[command][key]
        return translation


translation_file = open("asm_translation.json")
translations = json.load(translation_file)
translation_file.close()

translator = Translator(translations)

def get_vm_files_content(path):
    files_content = []
    os.chdir(path)
    file_name_list = [f for f in glob.glob("*.vm")]
    for vm_file_name in file_name_list:
        commands = [] 
        vm_file = open(vm_file_name)
        file_content = vm_file.read().split("\n")
        for line in file_content:
            comment_idx = line.find("//")
            clean_line = line.strip() if comment_idx==-1 else line[0:comment_idx].strip()
            if clean_line:
                arr = clean_line.split(" ")
                command = {"arg0":arr[0], "arg1":None if len(arr)<2 else arr[1],
                "arg2":None if len(arr)<3 else arr[2]}
                commands.append(command)
        files_content.append({"file_name":vm_file_name, "commands":commands})
    return files_content

def write_asm_translation(path, asm_file_name, asm_translation):
    os.chdir(path)
    asm_file = open(asm_file_name, "w")
    asm_file.write("")
    asm_file.close()
    asm_file = open(asm_file_name, "a")
    for command in asm_translation:
        asm_file.write(command+"\n")
    asm_file.close()

while True:
    path = input("Enter folder path or end to stop program execution: ")
    if path=="end":
        break
    asm_file_name = input("Enter asm file name: ")
    files_content = get_vm_files_content(path)
    write_asm_translation(path, asm_file_name, translator.translate(files_content))
