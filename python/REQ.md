# VIDEO generation

## TARGET

Make a python project, this is a command line tool to make video, based on given
materials

## Command line arguments

--folder: the project folder --sort: media material pickup order
--keep-clip-length: whether keep length of each clip, default is false.
--length: result video length in seconds --clip-num: number of clips. --title:
--title-font: the font for title --title-position: the position of title, this
is a number indicates how many percentage the title should be placed on screen's
height --subtle-font: the font for subtle --subtle-position: the position of
subtle, this is a number indicates how many percentage the subtle should be
placed on screen's height

## Project structure

In project folder, subfolders hold:

1. media: video clips and pictures
2. prompt: a prompt.md which is used to generate subtle(s),
3. subtle: in which there are subtle either LLM generated or user provided

## Process Steps

1. Read 'prompt.md', use LLM generate subtle
2. Generate audio use LLM API (TTS) to generate audio
3. Sort media files, combine them as one video

   3.1. if "--clip-num" exist, pick only that number of media files, or else,
   pick all in media folder

   3.2. if --sort value is 'alphnum', sort media's in alphnum order, if
   'random', place them randomly

   3.3. if --keep-clip-length is true, keep concatenating clips until the total
   length is longer than result video length specified with '--length'

   3.4. if --keep-clip-length is false, make a plan first, this plan will work
   out how many seconds will give to each clip, then, the clip will be cut from
   a random start to the length it is given, then be concatenated. Thus, at the
   end, the result video's length is equal to "--length"

4. always use 'starting.xxx' as the first clip, concatenate 'closing.xxx' as the
   last clip, 'xxx' could be any Video format
5. Add subtle and audio to the video, make the subtle sync with audio
6. Title is always show on the first clip, title text should not be wrapped, if
   there is ',' in title, split title by ',', the second and following element
   should placed under the first line, 90% font size of the first line.

## Effect

1. Use random transition effects

## Python and library

1. should use Python 3.12
2. Use libraries like "MoviePy", "PyDub", "FFmpeg" and any other libraries you
   think is necessary
