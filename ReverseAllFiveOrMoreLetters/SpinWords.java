import java.lang.*;
import java.util.*;
import java.util.function.Function;
import java.util.stream.*;

/*Write a function that takes in a string of one or more words, and returns the same string, but with all five or more letter words reversed (Just like the name of this Kata). Strings passed in will consist of only letters and spaces. Spaces will be included only when more than one word is present.
*/ 

public class SpinWords {

    private static String phrase1 = "Hey fellow warriors";
    private static String phrase2 = "This is a test";
    private static String phrase3 = "This is another test";
    public static void main(String[] args) {
        SpinWords wrds = new SpinWords();
        System.out.println(wrds.spinWords(phrase3));
    }

    //method 1
    public String spinWords(String sentence) {
        
        String[] words = sentence.split(" ");
        StringBuilder input = new StringBuilder();

        for(int i = 0; i < words.length; i++) {
            if(words[i].length() >= 5) {

                input.append(words[i]);
                words[i] = input.reverse().toString();
                input.delete(0, input.length());
            }
            else {
                continue;
            }
        }

        return String.join(" ", words);
    }

    //method 2
    public String spinWords2(String sentence) {
        
        return Arrays.stream(sentence.split(" "))
            .map(i -> i.length() > 4 ? new StringBuilder(i).reverse().toString() : i)
            .collect(Collectors.joining(" "));
    
    }

    //method 3
    public String spinWords3(String sentence) {

        for (String a : sentence.split(" ")) {
            if (a.length() > 4) {
                sentence = sentence.replace(a, new StringBuffer(a).reverse());
            }
        }
        return sentence;
    }
}