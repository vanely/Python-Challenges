public class Kata {
    public static int rentalCarCost(int d) {
        int total = 0;
        int rentalCost = 40;

        if(d >= 7) {
            return total = rentalCost * d - 50;
        }
        else if(d >= 3) {
            return total = rentalCost * d - 20;
        }
        else {
            return rentalCost * d;
        }
    }
}
