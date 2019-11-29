import argparse
import numpy as np
import os, sys
from numpy import linalg as LA
from numpy import linalg as la
import math
from PIL import Image
import random

try:
    sys.path.remove('/opt/ros/kinetic/lib/python2.7/dist-packages')
except:
    pass
import cv2


# -------------------------------------------------------------------------------
# @brief Function for converting gray scale to binary
#
#  @param Matrix
#
#  @return Matrix
#
def binary(A):
    for i in range(0, len(A)):
        for j in range(0, len(A[0])):
            # print(A[i,j])
            if (A[i, j] > 100):
                A[i, j] = 1
            else:
                A[i, j] = 0
    return A


# @brief Function for taking perspective transform
#
#  @param Image Matrix
#
#  @return Transformed Matrix
#
def perspective_view(image):
    # sequence tl,tr,br,bl
    dst1 = np.array([
        [0, 720],
        [0, 0],
        [1280, 0],
        [1280, 720]], dtype="float32")

    source = np.array([
        [0 + 150, 720 - 80],
        [0 + 570, 450],
        [1280 - 570, 450],
        [1280 - 50, 720 - 80]], dtype="float32")

    M1, status = cv2.findHomography(source, dst1)
    warp1 = cv2.warpPerspective(image, M1, (1280, 720))
    blur = cv2.GaussianBlur(warp1.copy(), (5, 5), 0)
    smooth = cv2.addWeighted(blur, 1.5, warp1, -0.5, 0)
    return smooth


# @brief Function for get back inverse perspective transform
#
#  @param Image Matrix
#
#  @return Transformed Matrix
#
def inverseperceptive(image):
    dst1 = np.array([
        [0, 720],
        [0, 0],
        [1280, 0],
        [1280, 720]], dtype="float32")

    source = np.array([
        [0 + 150, 720 - 80],
        [0 + 570, 450],
        [1280 - 570, 450],
        [1280 - 50, 720 - 80]], dtype="float32")

    M1, status = cv2.findHomography(dst1, source, )
    warp1 = cv2.warpPerspective(image.copy(), M1, (1280, 720))
    warp2 = cv2.medianBlur(warp1, 3)

    return warp2


# @brief Function for Undistorting image
#
#  @param Image Matrix
#
#  @return Transformed Matrix
#
def Undistort(image):
    dist = np.mat([-2.42565104e-01, -4.77893070e-02, -1.31388084e-03, -8.79107779e-05,
                   2.20573263e-02])

    K = np.mat([[1.15422732e+03, 0.00000000e+00, 6.71627794e+02],
                [0.00000000e+00, 1.14818221e+03, 3.86046312e+02],
                [0.00000000e+00, 0.00000000e+00, 1.00000000e+00]])

    destination = cv2.undistort(image, K, dist, None, K)

    return destination


# @brief Function for Extracting ROI
#
#  @param Image Matrix
#
#  @return Transformed Matrix
#
def ExtractROI(image, length, width):
    black = np.zeros((360, 1280))
    # Crop image
    imageROI = image[length:720, 0:1280]
    black = np.concatenate((black, imageROI), axis=0)
    return black


# @brief Function for yellow lane detection
#
#  @param Image Matrix, length and width of ROI
#
#  @return Transformed Matrix
#
def Yellowlane(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HLS)
    lower = np.array([20, 100, 100])
    upper = np.array([25, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)
    transform_y = perspective_view(mask)
    blur_y = cv2.GaussianBlur(transform_y.copy(), (5, 5), 0)
    return blur_y


# @brief Function for White lane detection
#
#  @param Image Matrix
#
#  @return Transformed Matrix
#
def Whitelane(image):
    # gray =cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    kernel_size = 5
    blur_gray = cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
    mask = cv2.inRange(blur_gray, 180, 255)
    # edges = cv2.Canny(gray,100,200)
    return mask


# @brief Function for getting Hough lines on image
#
#  @param Image Matrix and original image
#
#  @return Transformed Matrix
#
def Hough_lines(image, Original):
    width, height = image.shape

    edges = cv2.Canny(image, 100, 200)
    rho = np.ceil(np.sqrt(width * width + height * height))
    theta = np.pi / 60
    threshold = 6
    min_line_length = 30
    max_line_gap = 25
    line_image = np.copy(Original) * 0
    lines = cv2.HoughLinesP(edges, rho, theta, threshold, np.array([]), min_line_length, max_line_gap)

    for line in lines:
        for x1, y1, x2, y2 in line:
            cv2.line(line_image, (x1, y1), (x2, y2), (255, 0, 0), 5)

    # lines_edges = cv2.addWeighted(lines, 0.8, line_image, 1, 0)
    return line_image


# @brief Function for getting Histogram Silding
#
#  @param Image Matrix
#
#  @return left lane and right lane points
#
def Histogram(image):
    leftlane = []
    rightlane = []
    for j in range(10):
        c = 72 * (10 - j)
        d = 72 * (9 - j)
        for i in range(20):
            a = 64 * (i)
            b = 64 * (i + 1)
            img = image[d:c, a:b]
            hist = cv2.calcHist([img], [0], None, [3], [225, 285])
            # plt.plot(hist)
            # plt.show()
            # print(hist[4])
            if (hist[1] > 10 and i < 10):
                leftlane = np.append(leftlane, [(c + d) / 2, (a + b) / 2])
            if (hist[1] > 3 and 20 - i < 10):
                rightlane = np.append(rightlane, [(c + d) / 2, (a + b) / 2])
    rangeleft = int(leftlane.shape[0] / 2)
    left = np.reshape(leftlane, [rangeleft, 2])
    try:
        if (rightlane == []):
            raise ValueError

    except ValueError:
        rightlane = np.append(rightlane, leftlane[0])
        rightlane = np.append(rightlane, leftlane[1] + 800)
    rangeright = int(rightlane.shape[0] / 2)
    right = np.reshape(rightlane, [rangeright, 2])

    return image, left, right


# @brief Function for ploting on unwraped image
#
#  @param Image Matrix, Orignal Matrix, left lane, right lane
#
#  @return Transformed Matrix,slope
#
def plotlines(image, Original, left, right):
    left_fit = np.polyfit(left[:, 0], left[:, 1], 2)
    right_fit = np.polyfit(right[:, 0], right[:, 1], 2)

    window = np.linspace(0, image.shape[0] - 1, image.shape[0])
    left_fitx = left_fit[0] * window * window + left_fit[1] * window + left_fit[2]
    right_fitx = right_fit[0] * window * window + right_fit[1] * window + right_fit[2]
    center_line = (left_fit[0] * window * window + right_fit[0] * window * window) / 2 + (
            left_fit[1] * window + right_fit[1] * window) / 2 + (left_fit[2] + right_fit[2]) / 2
    black = Original * 0
    for i in range(window.shape[0]):
        y = int(window[i])
        x = int(left_fitx[i])
        x_r = int(right_fitx[i])
        x_c = int(center_line[i])
        total_lane = (x_r - x)
        for i in range(total_lane):
            if (x + i > 1280 - 1 or x + i < 0):
                break
            black[y, x + i] = [0, 0, 51]

    for j in range(5):
        if (x_c + j - 15 > 1280 - 1 or x_c + j - 15 < 0):
            break
        indexf = 120 + 120 * (j + 1) - 25
        indexi = 120 + 120 * (j) + 25
        pointf = (int(center_line[indexf]), int(window[indexf]))
        pointi = (int(center_line[indexi]), int(window[indexi]))
        cv2.arrowedLine(black, pointf, pointi, (0, 153, 76), 15, 4, 0, 0.5)
    slope = (math.atan((left_fitx[720 - 50] - left_fitx[50]) / 620)) * 180 / np.pi
    return black, slope


# @brief Function for text input in the Image
#
#  @param Image Matrix, slope
#
#  @return Transformed Matrix
#
def Text(image, slope):
    slp = round(slope, 2)
    info = "Angle of turning is: " + str(np.abs(slp)) + ' degrees'
    cv2.putText(image, info, (350, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (51, 0, 0), 3, cv2.LINE_AA)
    if (slp > 0):
        cv2.putText(image, 'Turn LEFT', (540, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 51, 102), 3, cv2.LINE_AA)
    elif (slp < 0):
        cv2.putText(image, 'Turn RIGHT', (540, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (51, 102, 0), 3, cv2.LINE_AA)
    else:
        cv2.putText(image, 'Go STRAIGHT', (540, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (51, 0, 102), 3, cv2.LINE_AA)

    return image


# -------------------------------------------------------------------------------
# @brief Function for pipeline for whole code
#
#  @param Path of Video
#
#  @return Array of images, size
#
def Pipeline(path):
    vidObj = cv2.VideoCapture(path)
    count = 0
    success = 1
    img_array = []
    while (success):
        if (count == 0):
            success, image = vidObj.read()

        from PIL import Image
        im = Image.fromarray(image)
        im.save('a.png')

        width, height, layers = image.shape
        size = (height, width)
        image = Undistort(image)
        undist_img = image.copy()
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        transform_w = perspective_view(gray)
        image_w = Whitelane(transform_w)
        image_y = Yellowlane(undist_img)
        final_transform = image_w + image_y
        final_transform_original = final_transform.copy()
        Histo, leftlane, rightlane = Histogram(final_transform)
        tr_with_lines, slope = plotlines(final_transform_original, undist_img, leftlane, rightlane)
        Lane_in_wrap = inverseperceptive(tr_with_lines)
        result = cv2.addWeighted(undist_img, 1, Lane_in_wrap, 1, 0)
        Final = Text(result, slope)
        count += 1
        print('Frame processing index')
        print(count)
        # cv2.imwrite('%d.jpg' %count,Final)
        img_array.append(Final)
        success, image = vidObj.read()

    return img_array, size


# video file
# @brief Function for video processing
#
#  @param Array of images, size
#
#  @return void
#
def video(img_array, size):
    video = cv2.VideoWriter('video.avi', cv2.VideoWriter_fourcc(*'DIVX'), 16.0, size)
    for i in range(len(img_array)):
        video.write(img_array[i])
    video.release()


def detect_lane(image):
    width, height, layers = image.shape
    image = Undistort(image)
    undist_img = image.copy()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    transform_w = perspective_view(gray)
    image_w = Whitelane(transform_w)
    image_y = Yellowlane(undist_img)
    final_transform = image_w + image_y
    final_transform_original = final_transform.copy()
    Histo, leftlane, rightlane = Histogram(final_transform)
    tr_with_lines, slope = plotlines(final_transform_original, undist_img, leftlane, rightlane)
    Lane_in_wrap = inverseperceptive(tr_with_lines)
    gray_merge = cv2.bitwise_or(undist_img, Lane_in_wrap)
    result = cv2.addWeighted(undist_img, 1, Lane_in_wrap, 1, 0)
    Final = Text(result, slope)
    slp = round(slope, 2)
    degree = np.abs(slp)

    touch = True
    return touch, degree, Final
