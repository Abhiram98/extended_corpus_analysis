from analyse_extended_corpus import analyse_data

analyse_data([
    "--projects_root_dir", "../projects",
    "--project_name", "CoreNLP",
    "--data_file", "../data/CoreNLP-data.json",
    "--jextract_out_dir", "../JExtractOut"
    ],
    standalone_mode=False)