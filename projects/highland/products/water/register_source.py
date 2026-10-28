import cv2,numpy as np,json
from pathlib import Path
out=Path(__file__).parent/'source-review'
a=cv2.imread(str(out/'unit-a.png'),0)
a=cv2.resize(a,(1824,1372))
b=cv2.imread(str(out/'P2.02-base.jpg'),0)
s=cv2.SIFT_create(nfeatures=15000,contrastThreshold=.018)
ka,da=s.detectAndCompute(a,None);kb,db=s.detectAndCompute(b,None)
m=cv2.BFMatcher().knnMatch(da,db,k=2);good=[x for x,y in m if x.distance<.68*y.distance]
pa=np.float32([ka[m.queryIdx].pt for m in good]);pb=np.float32([kb[m.trainIdx].pt for m in good])
M,inliers=cv2.estimateAffinePartial2D(pa,pb,method=cv2.RANSAC,ransacReprojThreshold=2,maxIters=10000)
sel=inliers.ravel().astype(bool);err=np.linalg.norm(pa@M[:,:2].T+M[:,2]-pb,axis=1)
print(json.dumps({'affine':M.tolist(),'matches':len(good),'inliers':int(sel.sum()),'median_residual_pdf_pt':float(np.median(err[sel])),'max_residual_pdf_pt':float(err[sel].max()),'source_extent':[[float(x) for x in pa[sel].min(0)],[float(x) for x in pa[sel].max(0)]]},indent=2))
(out/'registration.json').write_text(json.dumps({'affine':M.tolist(),'matches':len(good),'inliers':int(sel.sum()),'median_residual_pdf_pt':float(np.median(err[sel])),'max_residual_pdf_pt':float(err[sel].max())},indent=2))
v=cv2.drawMatches(a,ka,b,kb,[m for m,q in zip(good,sel) if q][::3],None,flags=2);cv2.imwrite(str(out/'registration-matches.jpg'),v)
