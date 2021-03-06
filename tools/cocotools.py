#! /usr/bin/env python
# coding=utf-8
# ================================================================
#
#   Author      : miemie2013
#   Created date: 2020-05-20 15:35:27
#   Description : coco评测
#
# ================================================================
import os
import json
import sys
import cv2
import shutil
import logging
logger = logging.getLogger(__name__)

clsid2catid = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9, 9: 10, 10: 11, 11: 13, 12: 14, 13: 15, 14: 16, 15: 17, 16: 18, 17: 19, 18: 20, 19: 21, 20: 22, 21: 23, 22: 24, 23: 25, 24: 27, 25: 28, 26: 31, 27: 32, 28: 33, 29: 34, 30: 35, 31: 36, 32: 37, 33: 38, 34: 39, 35: 40, 36: 41, 37: 42, 38: 43, 39: 44, 40: 46, 41: 47, 42: 48, 43: 49, 44: 50, 45: 51, 46: 52, 47: 53, 48: 54, 49: 55, 50: 56, 51: 57, 52: 58, 53: 59, 54: 60, 55: 61, 56: 62, 57: 63, 58: 64, 59: 65, 60: 67, 61: 70, 62: 72, 63: 73, 64: 74, 65: 75, 66: 76, 67: 77, 68: 78, 69: 79, 70: 80, 71: 81, 72: 82, 73: 84, 74: 85, 75: 86, 76: 87, 77: 88, 78: 89, 79: 90}

def get_classes(classes_path):
    with open(classes_path) as f:
        class_names = f.readlines()
    class_names = [c.strip() for c in class_names]
    return class_names

def cocoapi_eval(jsonfile,
                 style,
                 coco_gt=None,
                 anno_file=None,
                 max_dets=(100, 300, 1000)):
    """
    Args:
        jsonfile: Evaluation json file, eg: bbox.json, mask.json.
        style: COCOeval style, can be `bbox` , `segm` and `proposal`.
        coco_gt: Whether to load COCOAPI through anno_file,
                 eg: coco_gt = COCO(anno_file)
        anno_file: COCO annotations file.
        max_dets: COCO evaluation maxDets.
    """
    assert coco_gt != None or anno_file != None
    from pycocotools.coco import COCO
    from pycocotools.cocoeval import COCOeval

    if coco_gt == None:
        coco_gt = COCO(anno_file)
    logger.info("Start evaluate...")
    coco_dt = coco_gt.loadRes(jsonfile)
    if style == 'proposal':
        coco_eval = COCOeval(coco_gt, coco_dt, 'bbox')
        coco_eval.params.useCats = 0
        coco_eval.params.maxDets = list(max_dets)
    else:
        coco_eval = COCOeval(coco_gt, coco_dt, style)
    coco_eval.evaluate()
    coco_eval.accumulate()
    coco_eval.summarize()
    return coco_eval.stats

def bbox_eval(anno_file):
    from pycocotools.coco import COCO

    coco_gt = COCO(anno_file)

    outfile = 'eval_results/bbox_detections.json'
    logger.info('Generating json file...')
    bbox_list = []
    path_dir = os.listdir('eval_results/bbox/')
    for name in path_dir:
        with open('eval_results/bbox/' + name, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                r_list = json.loads(line)
                bbox_list += r_list
    with open(outfile, 'w') as f:
        json.dump(bbox_list, f)

    map_stats = cocoapi_eval(outfile, 'bbox', coco_gt=coco_gt)
    # flush coco evaluation result
    sys.stdout.flush()
    return map_stats

def eval(_decode, images, eval_pre_path, anno_file):
    # 8G内存的电脑并不能装下所有结果，所以把结果写进文件里。
    if os.path.exists('eval_results/bbox/'): shutil.rmtree('eval_results/bbox/')
    if not os.path.exists('eval_results/'): os.mkdir('eval_results/')
    os.mkdir('eval_results/bbox/')

    count = 0
    for im in images:
        im_id = im['id']
        file_name = im['file_name']
        image = cv2.imread(eval_pre_path + file_name)
        image, boxes, scores, classes = _decode.detect_image(image, draw_image=False)
        if boxes is not None:
            n = len(boxes)
            bbox_data = []
            for p in range(n):
                clsid = classes[p]
                score = scores[p]
                xmin, ymin, xmax, ymax = boxes[p]
                catid = (clsid2catid[int(clsid)])
                w = xmax - xmin + 1
                h = ymax - ymin + 1

                bbox = [xmin, ymin, w, h]
                # Round to the nearest 10th to avoid huge file sizes, as COCO suggests
                bbox = [round(float(x) * 10) / 10 for x in bbox]
                bbox_res = {
                    'image_id': im_id,
                    'category_id': catid,
                    'bbox': bbox,
                    'score': float(score)
                }
                bbox_data.append(bbox_res)
            path = 'eval_results/bbox/%.12d.json' % im_id
            with open(path, 'w') as f:
                json.dump(bbox_data, f)
        count += 1
        if count % 100 == 0:
            logger.info('Test iter {}'.format(count))
    # 开始评测
    box_ap_stats = bbox_eval(anno_file)
    return box_ap_stats


