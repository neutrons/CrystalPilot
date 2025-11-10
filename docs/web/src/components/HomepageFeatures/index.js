import React from 'react';
import clsx from 'clsx';
import styles from './styles.module.css';

const FeatureList = [
  {
    title: 'Based on Trame',
    Svg: require('@site/static/img/trame-text.svg').default,
    description: (
      <>
        Trame is an open-source platform for creating interactive and powerful visual analytics applications.
      </>
    ),
  },
  {
    title: 'Developed with NOVA',
    Svg: require('@site/static/img/science-area-icons-green_supercomputing.svg').default,
    description: (
      <>
        NOVA is a framework supporting development and deployment of applications with graphical user interfaces for Neutron Science.
      </>
    ),
  },
  {
    title: 'Integrated into NDIP',
    Svg: require('@site/static/img/logo.svg').default,
    description: (
      <>
        The Neutrons Data Interpretation Platform (NDIP) allows to run Neutron Science applications and workflows on ONRL's' compute infrastructure.
      </>
    ),
  },
];

function Feature({Svg, title, description}) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center">
        <Svg className={styles.featureSvg} role="img" />
      </div>
      <div className="text--center padding-horiz--md">
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures() {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
