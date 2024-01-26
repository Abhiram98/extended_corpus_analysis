import xml.etree.ElementTree as ET
import os
import click


def get():
    for module in all_modules:
        pathname = f"platform-{module}"
        # classpath_out = f'<classpathentry kind="src" path="{pathname}"/>'
        # print(classpath_out)
        fullpath = f"/Users/abhiram/Documents/JetGPT/extended_corpus/projects/intellij-community/platform/{module}/src"

        classpath_out = f'<classpathentry kind="src" path="{pathname}"/>'
        project_out = f"""
        <link>
            <name>{pathname}</name>
            <type>2</type>
            <location>{fullpath}</location>
        </link>
        """
        print(project_out)
        # print(project_out)
    pass


def convert(fullxml):
    # <classpathentry combineaccessrules="false" kind="src" path="/intellij.platform.lang"/>
    classpathxml = ET.fromstring(fullxml)
    for x in classpathxml:
        # x = ET.fromstring('<classpathentry combineaccessrules="false" kind="src" path="/intellij.platform.lang"/>')

        module = x.get('path').strip('/').split('.')
        if module[0] != 'intellij':
            continue

        pathname = "-".join(module[1:])
        dirpath = "/".join(module[1:])
        fullpath = f"/Users/abhiram/Documents/JetGPT/extended_corpus/projects/intellij-community/{dirpath}/src"
        if os.path.exists(fullpath)==False:
            print(fullpath)
            print("Doesn't exist")
            input()



        classpath_out = f'<classpathentry kind="src" path="{pathname}"/>'
        project_out = f"""
        <link>
            <name>{pathname}</name>
            <type>2</type>
            <location>{fullpath}</location>
        </link>
        """
        # print(project_out)
        print(classpath_out)

    pass

@click.command()
@click.option("--project_dir", help="Location of project to create "
                                    ".project and .classpath files for")
def create_project_classpath():
    # TODO: recurse through platform/*
    # Find all src folders.
    # if there is a "test" in the folder, exclude.
    # Add to .classpath
    # Add to .project
    rootdir = 'projects/intellij-community/platform'

    for subdir, dirs, files in os.walk(rootdir):
        for file in files:
            print(os.path.join(subdir, file))

    return

if __name__ == '__main__':
    pass
