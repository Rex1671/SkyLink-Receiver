
echo "========================================"
echo " Android Stream Receiver"
echo "========================================"
echo ""
echo "Choose receiver type:"
echo "  1. Simple (Console only, no OpenCV)"
echo "  2. Single Camera (OpenCV)"
echo "  3. Dual Camera (OpenCV)"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        python3 receiver_simple.py
        ;;
    2)
        read -p "Camera (back/front): " camera
        python3 receiver_opencv.py --camera $camera
        ;;
    3)
        python3 receiver_dual.py
        ;;
    *)
        echo "Invalid choice"
        ;;
esac
