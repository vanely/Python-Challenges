public class Kata {

    //Theater One
    private static int totalCols1 = 16;
    private static int totalRows1 = 11;
    private static int seatCol1 = 5;
    private static int seatRow1 = 3;

    //Theater One
    private static int totalCols2 = 1;
    private static int totalRows2 = 1;
    private static int seatCol2 = 1;
    private static int seatRow2 = 1;

    // Theater One
    private static int totalCols3 = 13;
    private static int totalRows3 = 6;
    private static int seatCol3 = 8;
    private static int seatRow3 = 3;

    public static void main(String[] args) {

        System.out.println(seatsInTheater(totalCols3, totalRows3, seatCol3, seatRow3));
    }

    public static int seatsInTheater(int nCols, int nRows, int col, int row) {

        return (nCols - (col - 1)) * (nRows - row);

    }

}