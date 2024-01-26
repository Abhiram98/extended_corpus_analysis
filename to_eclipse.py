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
def create_project_classpath(project_dir):
    # TODO: recurse through platform/*
    # Find all src folders.
    # if there is a "test" in the folder, exclude.
    # Add to .classpath
    # Add to .project
    rootdir = 'projects/intellij-community/platform'

    project_xml = ET.parse("base.project")
    classpath_xml = ET.parse("base.classpath")

    sub_projects = []
    count = 0
    linked_resources = ET.fromstring("<linkedResources></linkedResources>")
    for subdir, dirs, files in os.walk(rootdir):
        if 'src' in dirs:
            count+=1
            sub_projects.append(os.path.join(subdir, 'src'))
            if 'test' in subdir:
                continue

            link_name = "-".join(subdir.split('intellij-community/')[1].split('/'))
            if link_name=='platform-impl':
                continue
            fullpath = os.path.abspath(os.path.join(subdir, 'src'))
            project_out = f"""
<link>
    <name>{link_name}</name>
    <type>2</type>
    <location>{fullpath}</location>
</link>
            """
            x = ET.fromstring(project_out)
            linked_resources.append(x)

            classpath_out = f'<classpathentry kind="src" path="{link_name}"/>'
            c = ET.fromstring(classpath_out)
            classpath_xml.getroot().insert(1, c)

    project_xml.getroot().append(linked_resources)

    with open(f"{project_dir}/.project", 'wb') as f:
        project_xml.write(f)
    with open(f"{project_dir}/.classpath", 'wb') as f:
        classpath_xml.write(f)

    with open(f"projects/.intellij-communityproject", 'wb') as f:
        project_xml.write(f)
    with open(f"projects/.intellij-communityclasspath", 'wb') as f:
        classpath_xml.write(f)

    with open(f"test.project", 'wb') as f:
        project_xml.write(f)
    with open(f"test.classpath", 'wb') as f:
        classpath_xml.write(f)


    print(sub_projects)


    return

if __name__ == '__main__':
    create_project_classpath(["--project_dir",
                              "projects/intellij-community/platform/platform-impl"],
                             standalone_mode=False)
