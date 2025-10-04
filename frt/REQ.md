# A content management service

the source code of 'frt' (which means front-end) is brought from a translation
service application, we need to modify it to make a new video content management
service.

this is a svelete5 project, for APIs reference, go to

<https://svelte.dev/docs/svelte/overview>
<https://svelte.dev/docs/kit/introduction> and context7

Requirements are:

## Back-end folder structure

1. a vault folder to hold assets, the vault is configured by env:
   AIV_VAULT_FODLER
2. vault/media: for public media files
3. each user's home is under vault, like vault/user_name
4. vault/user_name/media: for user level media files
5. projects of user are placed in vault/user_name/project_name
6. the project folder structure is:
   - media: project level media files
   - output: store generated videos
   - prompt: store one single 'prompt.md' file
   - subtitle: store subtitle files

## Front-end application

The front-end application allow user to:

- create project
- view project
- modify project
- copy project to a new one
- delete project

## Project definition

a project organize video information which will be used to generate a video(also
known as final video or result video) a project has following attributes:

- name: project name, should be unique at user level
- title: the title of final video
- prompt: the prompt text for subtitle generation
- static subtitle: if provided, will not generate using prompt.

## User could

- edit prompt: edit the content of 'prompt.md'
- upload new media which are picture or video, allow upload to public-level,
  user-level or project level media folder
- maintenance a list of media (call them project materials) which will be used
  for current project, the media candidates could be selected from three levels
  media folder, so, the materials are a subset of the combination of public
  media, user media and project media.
- preview media: display picture or play video
- generate video by click a button to invoke the 'python main.py' in 'python'
  folder could see python program log could preview the result

## OTHER REQUIREMENTS

- You should also check the command line argument of "python/main.py" and
  "python/config_module.py", map those argument to be a configuration UI
  component in frt svelte5
- use apple liquid glass style, try to search to make your best effect to make
  it the same as Apple designed liquid glass CSS
- PC web browser and Mobile phone browser auto-adapt
