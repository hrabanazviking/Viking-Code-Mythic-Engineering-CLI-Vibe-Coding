# Old Norwegian Dictionary

Old Norwegian/Norse Dictionary for Node.js. The dictionary consists of 40 000+ Old Norse words with Norwegian translations.

Based on "Dictionary of the Old Norwegian Language".

Related projects:
- [Old Norwegian Dictionary website in Next.js](https://github.com/stscoundrel/old-norwegian-dictionary-next)
- [Old Norwegian Dictionary Abbreviations](https://github.com/stscoundrel/old-norwegian-dictionary-abbreviations).
- [Old Norwegian Dictionary Builder](https://github.com/stscoundrel/old-norwegian-dictionary-builder).

Ports in other languages:
- [Go](https://github.com/stscoundrel/old-norwegian-dictionary-go)
- [C# / .NET](https://github.com/stscoundrel/old-norwegian-dictionary-cs)
- [Python](https://github.com/stscoundrel/old-norwegian-dictionary-py)
- [Rust](https://github.com/stscoundrel/old-norwegian-dictionary-rs)

### Install

`yarn add old-norwegian-dictionary`

### Usage

The project provides a getter for the whole dataset. You can use it in your script to populate your own database or otherwise use the data.

Should you want to use the data without this Node.js library, you might want to check [Old Norwegian Dictionary Builder](https://github.com/stscoundrel/old-norwegian-dictionary-builder)


```javascript
import { getDictionary } from 'old-norwegian-dictionary'

/**
 * Whole dictionary as array
 * contains over 40 000 entries.
 */
const dictionary = getDictionary()


// Filter words starting with letter T
const tWords = dictionary.filter((entry) => entry.word.charAt(0) === 't')

console.log(tWords)

```

Individual words are returned in format of:

```javascript
{
    word:         String   // eg. griðabeiðandi
    partOfSpeech: String   // eg. m
    definition:   String   // eg. riðabeiðandi, m. Person som begjærer grið 3. Grág. 30716.
}
```


### About "Dictionary of the Old Norwegian Language"

_"Ordbog over det gamle norske Sprog"_ dictionary was published in late 1800s by Johan Fritzner. Its is the largest Old Norse to Norwegian dictionary, containing over 40 000 word definitions. While the original dictionary is called dictionary of "old norwegian", it is practically a dictionary of western Old Norse. Technically "Old Norwegian" would be a later stage in the language.
